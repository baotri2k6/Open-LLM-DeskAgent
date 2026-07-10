"""
refactor_avatar_pet.py
Replaces hardcoded MODEL_ACCESSORIES / getModelKey in avatar-pet.js
with AssetRegistry lookups.
"""
import pathlib

p = pathlib.Path("renderer/avatar/avatar-pet.js")
src = p.read_text(encoding="utf-8")

# ─── 1. Remove currentModelPath + getModelKey + MODEL_ACCESSORIES block ───────
# The block starts at 'let currentModelPath' and ends at '  hiyori: [],' + next line '};'
START = "let currentModelPath ="
END_SENTINEL = "  hiyori: [],\n};"

s_idx = src.find(START)
e_idx = src.find(END_SENTINEL)
if s_idx == -1 or e_idx == -1:
    print("WARNING: Could not find MODEL_ACCESSORIES block — already removed or changed?")
else:
    e_idx += len(END_SENTINEL)
    replacement = (
        "// currentModelId stores the active model identifier (registry id string)\n"
        "// Initialized after AssetRegistry is loaded in applyInitialMode.\n"
        "let currentModelId = 'icegirl';\n"
    )
    src = src[:s_idx] + replacement + src[e_idx:]
    print("Removed MODEL_ACCESSORIES block.")

# ─── 2. Patch rebuildAccessoryButtons signature + first few lines ─────────────
OLD_HDR = (
    'function rebuildAccessoryButtons(modelPath) {\n'
    '  const container = document.getElementById("characterPropsRow");\n'
    '  if (!container) return;\n'
    '  container.innerHTML = "";\n'
    '\n'
    '  const modelKey = getModelKey(modelPath);\n'
    '  const accessories = MODEL_ACCESSORIES[modelKey] || [];'
)
NEW_HDR = (
    'function rebuildAccessoryButtons(modelId) {\n'
    '  const container = document.getElementById("characterPropsRow");\n'
    '  if (!container) return;\n'
    '  container.innerHTML = "";\n'
    '\n'
    '  const accessories = AssetRegistry.getAccessories(modelId);'
)
if OLD_HDR in src:
    src = src.replace(OLD_HDR, NEW_HDR, 1)
    print("Patched rebuildAccessoryButtons header.")
else:
    print("WARNING: rebuildAccessoryButtons header not found — check whitespace.")

# ─── 3. Patch config:updated handler for app.avatarModel ─────────────────────
OLD_CFG = (
    '  } else if (key === "app.avatarModel") {\n'
    '    avatar.changeModel(value);\n'
    '    currentModelPath = value;\n'
    '    rebuildAccessoryButtons(value);\n'
    "    setCaption(`\u0110\u00e3 \u0111\u1ed5i nh\u00e2n v\u1eadt th\u00e0nh c\u00f4ng!`);\n"
    '  }'
)
NEW_CFG = (
    '  } else if (key === "app.avatarModel") {\n'
    '    // value may be a path or an id \u2014 resolve via registry\n'
    '    const resolvedId = AssetRegistry.resolvePathToId(value);\n'
    '    avatar.changeModel(value);\n'
    '    currentModelId = resolvedId;\n'
    '    rebuildAccessoryButtons(resolvedId);\n'
    "    setCaption(`\u0110\u00e3 \u0111\u1ed5i nh\u00e2n v\u1eadt th\u00e0nh c\u00f4ng!`);\n"
    '  }'
)
if OLD_CFG in src:
    src = src.replace(OLD_CFG, NEW_CFG, 1)
    print("Patched config:updated app.avatarModel handler.")
else:
    print("WARNING: config:updated handler not found.")

# ─── 4. Patch applyInitialMode to use currentModelId ─────────────────────────
OLD_APPLY = (
    '      if (res.avatar_model) {\n'
    '        if (currentModelPath !== res.avatar_model) {\n'
    '          currentModelPath = res.avatar_model;\n'
    '          avatar.changeModel(res.avatar_model);\n'
    '        }\n'
    '      }\n'
    '\n'
    '      rebuildAccessoryButtons(currentModelPath);'
)
NEW_APPLY = (
    '      if (res.avatar_model) {\n'
    '        const newId = AssetRegistry.resolvePathToId(res.avatar_model);\n'
    '        if (currentModelId !== newId) {\n'
    '          currentModelId = newId;\n'
    '          avatar.changeModel(res.avatar_model);\n'
    '        }\n'
    '      }\n'
    '\n'
    '      rebuildAccessoryButtons(currentModelId);'
)
if OLD_APPLY in src:
    src = src.replace(OLD_APPLY, NEW_APPLY, 1)
    print("Patched applyInitialMode.")
else:
    print("WARNING: applyInitialMode block not found.")

# ─── Write ────────────────────────────────────────────────────────────────────
p.write_text(src, encoding="utf-8")
print(f"Done. File size: {p.stat().st_size} bytes")
