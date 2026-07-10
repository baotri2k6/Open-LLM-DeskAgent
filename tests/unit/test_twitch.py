import pytest
from unittest.mock import MagicMock, patch
from interaction.chat.twitch_bridge import TwitchBridge
from social.moderation.content_moderator import ContentModerator


def test_content_moderation_rules():
    moderator = ContentModerator()
    
    # 1. Clean message
    res_clean = moderator.evaluate("ViewerA", "Chào bạn, hôm nay thế nào rồi?")
    assert res_clean["is_flagged"] is False

    # 2. Toxic message
    res_toxic = moderator.evaluate("ViewerB", "Mày là đồ ngốc thế hả shit fck!")
    assert res_toxic["is_flagged"] is True
    assert res_toxic["reason"] == "toxic_language"

    # 3. Caps spam message
    res_caps = moderator.evaluate("ViewerC", "HELLOMAYLADOCHOIQUAXADI")
    assert res_caps["is_flagged"] is True
    assert res_caps["reason"] == "spam"

    # 4. Add custom word
    moderator.add_blacklisted_word("cà khịa")
    res_custom = moderator.evaluate("ViewerD", "Muốn đi cà khịa ghê")
    assert res_custom["is_flagged"] is True
    assert res_custom["reason"] == "toxic_language"


@pytest.mark.anyio
async def test_twitch_bridge_event_publishing():
    from runtime.eventbus.event_bus import event_bus
    from runtime.events.event_types import EventType

    bridge = TwitchBridge("TestChannel")
    
    published_events = []
    def spy_publish(event):
        published_events.append(event)

    with patch.object(event_bus, "publish", side_effect=spy_publish):
        # Trigger moderated clean message
        bridge._handle_incoming_message("ViewerA", "Chào cả nhà")
        assert len(published_events) == 1
        assert published_events[0].event_type == EventType.VOICE_DETECTED
        assert published_events[0].payload["text"] == "Chào cả nhà"
        assert published_events[0].payload["username"] == "ViewerA"

        # Trigger flagged message - should not publish to EventBus
        bridge._handle_incoming_message("ViewerB", "Đồ ngốc nghếch fck")
        assert len(published_events) == 1  # Still 1


def test_twitch_adaptive_throttle():
    from api.server import _should_reply, handle_twitch_msg, _msg_timestamps, _recent_twitch_messages
    import time
    
    # Reset state
    _msg_timestamps.clear()
    _recent_twitch_messages.clear()
    
    # 1. Test sparse chat (< 10 msg/min)
    assert _should_reply(5) is True
    assert _should_reply(10) is True
    
    # 2. Test dense chat (> 10 msg/min)
    # With random mocked to 0.1 (< 0.3) -> should reply
    with patch("random.random", return_value=0.1):
        assert _should_reply(15) is True
        
    # With random mocked to 0.5 (>= 0.3) -> should not reply
    with patch("random.random", return_value=0.5):
        assert _should_reply(15) is False

    # 3. Test handle_twitch_msg and moderation interaction
    # Clean message should be recorded in timestamps
    handle_twitch_msg("ViewerA", "Chào bạn")
    assert len(_recent_twitch_messages) == 1
    assert len(_msg_timestamps) == 1
    
    # Flagged message should not be recorded
    handle_twitch_msg("ViewerB", "Mày là đồ ngốc thế hả shit fck!")
    assert len(_recent_twitch_messages) == 1  # Still 1
    assert len(_msg_timestamps) == 1  # Still 1
