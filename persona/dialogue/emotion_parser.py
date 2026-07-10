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
    """Parses emotion tags [emotion] and thinking tags <think> from the LLM stream."""

    def __init__(self) -> None:
        self.buffer = ""
        self.in_thought = False

    def feed(self, token: str) -> dict | None:
        self.buffer += token
        
        # 1. Check for thinking tags
        for think_start in ["<think>", "<thought>"]:
            if think_start in self.buffer:
                self.buffer = self.buffer.replace(think_start, "(suy nghĩ: ")
                self.in_thought = True

        for think_end in ["</think>", "</thought>"]:
            if think_end in self.buffer:
                self.buffer = self.buffer.replace(think_end, ")\n")
                self.in_thought = False

        # 2. Check for bracket emotion tags
        match = TAG_PATTERN.search(self.buffer)
        if match:
            tag = match.group(0)
            emotion = match.group(1).lower()
            self.buffer = self.buffer.replace(tag, "")
            return {"type": "emotion", "emotion": emotion}

        # 3. Check for emojis
        for emoji, emotion in EMOJI_TO_EMOTION.items():
            if emoji in self.buffer:
                self.buffer = self.buffer.replace(emoji, "")
                return {"type": "emotion", "emotion": emotion}

        return None

    def flush_text(self) -> str:
        """Flush clean text from buffer, leaving partial tags untouched."""
        idx = self.buffer.find("[")
        idx_angle = self.buffer.find("<")
        
        if idx == -1 and idx_angle == -1:
            text_to_send = self.buffer
            self.buffer = ""
            return text_to_send
            
        # Find the earliest tag start
        indices = [i for i in [idx, idx_angle] if i != -1]
        first_idx = min(indices)
        
        if first_idx > 0:
            text_to_send = self.buffer[:first_idx]
            self.buffer = self.buffer[first_idx:]
            return text_to_send
        else:
            # Buffer starts with '[' or '<', wait to see if it forms a tag
            if len(self.buffer) > 20:
                text_to_send = self.buffer
                self.buffer = ""
                return text_to_send
            return ""

    def flush_all(self) -> str:
        """Force flush all remaining text in buffer."""
        res = self.buffer
        self.buffer = ""
        return res
