const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

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

assert.strictEqual(normalizeMotion("greeting"), "nod");
assert.strictEqual(normalizeMotion("focus"), "thinking");
assert.strictEqual(getMotionForEmotion("happy"), "excited");
assert.strictEqual(getMotionForEmotion("thinking"), "thinking");
assert.strictEqual(getMotionForEmotion("angry"), "shake");
assert.strictEqual(getMotionForEmotion("surprised"), "surprised");

console.log("motion system tests passed");
