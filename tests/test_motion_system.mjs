import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const motionPath = path.join(__dirname, "..", "live2d", "motions", "motion.js");
const source = fs.readFileSync(motionPath, "utf8");
const transformed = source
  .replace(/export const /g, "const ")
  .replace(/export function /g, "function ")
  .replace(/export \{[^}]+\};?/g, "");

const module = { exports: {} };
const context = { module, exports: module.exports, console };
vm.createContext(context);
vm.runInContext(
  `${transformed}\nmodule.exports = { MOTION_MAPPINGS, normalizeMotion, getMotionForEmotion };`,
  context,
);

const { normalizeMotion, getMotionForEmotion } = module.exports;

assert.equal(normalizeMotion("greeting"), "nod");
assert.equal(normalizeMotion("focus"), "thinking");
assert.equal(getMotionForEmotion("happy"), "excited");
assert.equal(getMotionForEmotion("thinking"), "thinking");
assert.equal(getMotionForEmotion("angry"), "shake");
assert.equal(getMotionForEmotion("surprised"), "surprised");

console.log("motion system tests passed");
