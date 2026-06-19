import re

EMOJI_TO_EMOTION = {
    # Smile/Happy
    "😊": "smile", "😄": "smile", "😀": "smile", "🙂": "smile",
    "😂": "happy", "😆": "happy", "😸": "happy",
    # Love/Happy
    "❤️": "happy", "😍": "happy", "🥰": "happy",
    # Excited
    "🤩": "excited", "🌟": "excited", "✨": "excited",
    # Thinking
    "🤔": "thinking", "🧐": "thinking", "💭": "thinking",
    # Sad
    "😭": "sad", "😢": "sad", "🥺": "sad", "😿": "sad",
    # Angry
    "😡": "angry", "😠": "angry", "🤬": "angry", "👿": "angry",
    # Surprised
    "😱": "surprised", "😲": "surprised", "😮": "surprised", "😳": "surprised",
    # Wink
    "😉": "wink", "😜": "wink",
    # Tongue
    "😛": "tongue", "😝": "tongue",
    # Money
    "🤑": "money", "💵": "money", "💰": "money",
}

# Regex to match bracket tags: [happy], [sad], etc.
TAG_PATTERN = re.compile(
    r"\[(normal|neutral|smile|friendly|happy|excited|focused|thinking|sad|angry|surprised|wink|tongue|money)\]",
    re.IGNORECASE
)

class EmotionStreamParser:
    def __init__(self) -> None:
        self.buffer = ""

    def feed(self, token: str) -> dict | None:
        self.buffer += token
        
        # 1. Check for bracket tags
        match = TAG_PATTERN.search(self.buffer)
        if match:
            tag = match.group(0)
            emotion = match.group(1).lower()
            self.buffer = self.buffer.replace(tag, "")
            return {"type": "emotion", "emotion": emotion}

        # 2. Check for emojis
        for emoji, emotion in EMOJI_TO_EMOTION.items():
            if emoji in self.buffer:
                self.buffer = self.buffer.replace(emoji, "")
                return {"type": "emotion", "emotion": emotion}

        return None

    def flush_text(self) -> str:
        idx = self.buffer.find("[")
        if idx == -1:
            text_to_send = self.buffer
            self.buffer = ""
            return text_to_send
        elif idx > 0:
            text_to_send = self.buffer[:idx]
            self.buffer = self.buffer[idx:]
            return text_to_send
        else:
            # Buffer starts with '[', wait to see if it forms a tag
            if len(self.buffer) > 15:
                text_to_send = self.buffer
                self.buffer = ""
                return text_to_send
            return ""

    def flush_all(self) -> str:
        res = self.buffer
        self.buffer = ""
        return res
