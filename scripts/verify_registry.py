import pathlib, json

def check(label, cond):
    print("  " + ("OK  " if cond else "FAIL") + " " + label)

pet = pathlib.Path("renderer/avatar/avatar-pet.js").read_text(encoding="utf-8")
print("=== avatar-pet.js ===")
check("AssetRegistry import present",      "import { AssetRegistry }" in pet)
check("MODEL_ACCESSORIES removed",          "MODEL_ACCESSORIES" not in pet)
check("getModelKey removed",                "function getModelKey" not in pet)
check("rebuildAccessoryButtons(modelId)",   "rebuildAccessoryButtons(modelId)" in pet)
check("AssetRegistry.getAccessories used",  "AssetRegistry.getAccessories" in pet)
check("currentModelId defined",             "let currentModelId" in pet)
check("resolvePathToId used",               "AssetRegistry.resolvePathToId" in pet)

mgr = pathlib.Path("live2d/live2d-manager.js").read_text(encoding="utf-8")
print("=== live2d-manager.js ===")
check("AssetRegistry import present",          "import { AssetRegistry }" in mgr)
check("getModelKey removed",                    "function getModelKey" not in mgr)
check("MODEL_PATH removed",                     "const MODEL_PATH" not in mgr)
check("getScale used in _fitModel",             "AssetRegistry.getScale" in mgr)
check("getExpressionFallback used",             "AssetRegistry.getExpressionFallback" in mgr)
check("getHitReactions used in handleTap",      "AssetRegistry.getHitReactions" in mgr)
check("AssetRegistry.load() in _init",          "AssetRegistry.load()" in mgr)
check("resolvePathToId in changeModel",         "AssetRegistry.resolvePathToId" in mgr)

reg = pathlib.Path("live2d/asset-registry.js")
print("=== asset-registry.js: " + str(reg.stat().st_size) + " bytes ===")

m = json.loads(pathlib.Path("assets/live2d/models.json").read_text(encoding="utf-8"))
print("=== models.json: " + str(len(m["models"])) + " models ===")
for model in m["models"]:
    print("  - " + model["id"] + " (" + str(len(model["accessories"])) + " accessories, default=" + str(model["default"]) + ")")
