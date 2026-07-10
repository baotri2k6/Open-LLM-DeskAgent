"""Twitch bridge — connects to Twitch IRC, moderates incoming comments and routes to EventBus."""

from __future__ import annotations

import logging
import random
import socket
import re
import threading
import time
from typing import Callable, Optional

from config.config import config
from runtime.eventbus.event_bus import event_bus
from runtime.events.base_event import BaseEvent
from runtime.events.event_types import EventType
from social.moderation.content_moderator import content_moderator

logger = logging.getLogger("ai-companion.social.twitch")


class TwitchBridge:
    """TwitchBridge handles Twitch IRC connection, moderation filtering and event routing."""

    def __init__(self, channel: str, message_callback: Optional[Callable[[str, str], None]] = None) -> None:
        self.channel = channel.lower().strip().lstrip("#")
        self.message_callback = message_callback
        self.running = False
        self.socket: Optional[socket.socket] = None
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info("TwitchBridge: Started background IRC reader for channel: %s", self.channel)

    def stop(self) -> None:
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
        logger.info("TwitchBridge: Stopped background IRC reader")

    def _run(self) -> None:
        while self.running:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(10.0)
                logger.info("TwitchBridge: Connecting to irc.chat.twitch.tv:6667")
                self.socket.connect(("irc.chat.twitch.tv", 6667))
                
                # Anonymous credentials
                nick = f"justinfan{random.randint(10000, 99999)}"
                self.socket.send(f"PASS oauth:anything\r\n".encode("utf-8"))
                self.socket.send(f"NICK {nick}\r\n".encode("utf-8"))
                self.socket.send(f"JOIN #{self.channel}\r\n".encode("utf-8"))
                
                logger.info("TwitchBridge: Joined channel #%s", self.channel)
                
                buffer = ""
                while self.running:
                    try:
                        data = self.socket.recv(4096).decode("utf-8", errors="ignore")
                        if not data:
                            logger.warning("TwitchBridge: Socket disconnected")
                            break
                        buffer += data
                        while "\r\n" in buffer:
                            line, buffer = buffer.split("\r\n", 1)
                            if line.startswith("PING"):
                                self.socket.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                            elif "PRIVMSG" in line:
                                # Parse sender and message
                                match = re.match(r":([^!]+)![^ ]+ PRIVMSG #[^ ]+ :(.*)", line)
                                if match:
                                    username = match.group(1)
                                    message_text = match.group(2)
                                    self._handle_incoming_message(username, message_text)
                    except socket.timeout:
                        continue
                    except Exception as e:
                        logger.warning("TwitchBridge socket read error: %s", e)
                        break
            except Exception as e:
                logger.warning("TwitchBridge connection error: %s", e)
            
            # Wait before reconnecting
            if self.running:
                time.sleep(5)

    def _handle_incoming_message(self, username: str, message: str) -> None:
        # Run content moderation check
        eval_res = content_moderator.evaluate(username, message)
        if eval_res.get("is_flagged"):
            logger.warning(
                "TwitchBridge: Flagged message from %s (Reason: %s, Action: %s). Dropping message.",
                username, eval_res.get("reason"), eval_res.get("action")
            )
            return

        logger.info("TwitchBridge: Received moderated message from @%s: %s", username, message)
        
        # Publish payload to EventBus for perception / commentator loop ingestion
        try:
            event = BaseEvent.create(
                event_type=EventType.VOICE_DETECTED,  # Routes to perception stream
                source="twitch_bridge",
                payload={"text": message, "username": username, "channel": self.channel}
            )
            event_bus.publish(event)
        except Exception as e:
            logger.error("TwitchBridge: Failed to publish message to EventBus: %s", e)

        # Trigger message callback if provided
        if self.message_callback:
            try:
                self.message_callback(username, message)
            except Exception as e:
                logger.error("TwitchBridge: Callback execution failed: %s", e)
