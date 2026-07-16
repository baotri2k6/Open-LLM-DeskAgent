import json
from pathlib import Path
from runtime.logger import get_logger

logger = get_logger("character.registry")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHARACTERS_DIR = PROJECT_ROOT / "characters"
REGISTRY_FILE = CHARACTERS_DIR / "registry.json"
LEGACY_MODELS_FILE = PROJECT_ROOT / "assets" / "live2d" / "models.json"


class CharacterRegistry:
    def __init__(self):
        self.characters = []
        self._load()

    def _load(self):
        if not REGISTRY_FILE.exists():
            logger.warning(f"Character registry not found at {REGISTRY_FILE}. Initializing empty.")
            self.characters = []
            return

        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            self.characters = []
            for entry in data.get("characters", []):
                char_path = PROJECT_ROOT / entry.get("path", "")
                if char_path.exists():
                    try:
                        with open(char_path, "r", encoding="utf-8") as cf:
                            char_data = json.load(cf)
                            # Bổ sung các thông tin từ registry entry
                            char_data["_default"] = entry.get("default", False)
                            self.characters.append(char_data)
                    except Exception as e:
                        logger.error(f"Failed to load character file {char_path}: {e}")
                else:
                    logger.warning(f"Character path not found: {char_path}")
                    
            self._sync_legacy_models_json()
        except Exception as e:
            logger.error(f"Failed to load registry {REGISTRY_FILE}: {e}")

    def get_all(self):
        return self.characters

    def get_by_id(self, char_id: str):
        for char in self.characters:
            if char.get("id") == char_id:
                return char
        return None

    def _sync_legacy_models_json(self):
        """Tự động generate assets/live2d/models.json từ dữ liệu characters/ để backward compatibility."""
        try:
            legacy_models = []
            for char in self.characters:
                # Map cấu trúc mới sang cấu trúc models.json cũ
                model_data = char.get("model", {})
                images_data = char.get("images", {})
                
                # Convert new path to string for thumbnail if it exists
                thumbnail = images_data.get("avatar") or images_data.get("card")
                if not thumbnail:
                    # Fallback
                    thumbnail = None

                legacy_model = {
                    "id": char.get("id", ""),
                    "name": char.get("name", ""),
                    "description": char.get("description", ""),
                    "path": model_data.get("path", ""),
                    "thumbnail": thumbnail,
                    "scale": model_data.get("scale", 1.0),
                    "default": char.get("_default", False),
                    "tags": char.get("tags", []),
                    "accessories": char.get("accessories", []),
                    "hitReactions": char.get("hitReactions", {}),
                    "expressionFallback": char.get("expressionFallback", {})
                }
                legacy_models.append(legacy_model)

            legacy_data = {
                "version": "1.0.0",
                "models": legacy_models
            }

            LEGACY_MODELS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(LEGACY_MODELS_FILE, "w", encoding="utf-8") as f:
                json.dump(legacy_data, f, indent=2, ensure_ascii=False)
                
            logger.info("Successfully synced legacy models.json from character registry.")
        except Exception as e:
            logger.error(f"Failed to sync legacy models.json: {e}")

    def reload(self):
        self._load()

    def remove_character(self, char_id: str) -> bool:
        """Removes a character from registry.json and reloads."""
        if not REGISTRY_FILE.exists():
            return False

        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            characters = data.get("characters", [])
            before_len = len(characters)
            
            # Remove from registry.json
            data["characters"] = [c for c in characters if c.get("id") != char_id]
            
            if len(data["characters"]) == before_len:
                return False

            with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            # Delete the character folder in characters/
            char_dir = CHARACTERS_DIR / char_id
            if char_dir.exists() and char_dir.is_dir():
                import shutil
                try:
                    shutil.rmtree(char_dir)
                except Exception as e:
                    logger.warning(f"Could not delete character folder {char_dir}: {e}")

            self.reload()
            return True
        except Exception as e:
            logger.error(f"Failed to remove character {char_id}: {e}")
            return False

character_registry = CharacterRegistry()
