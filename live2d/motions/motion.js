/**
 * motion.js — map tên motion → Live2D motion name
 *
 * Motion files trong assets/live2d/IceGirl/motions/:
 *   DaiJi.motion3.json   — chờ / standby
 *   HuiShou.motion3.json — quay đầu / look aside
 *   MeiYan.motion3.json  — nheo mắt / squint
 */

export const MOTION_TO_LIVE2D = {
  idle: "DaiJi",
  nod: "MeiYan", // không có nod riêng → dùng MeiYan
  shake: "HuiShou", // lắc đầu nhẹ
  thinking: "DaiJi",
  look_side: "HuiShou",
  excited: "MeiYan",
};

export const MOTION_MAPPINGS = {
  icegirl: {
    idle: "DaiJi",
    nod: "MeiYan",
    shake: "HuiShou",
    thinking: "DaiJi",
    look_side: "HuiShou",
    excited: "MeiYan",
    sad: "DaiJi",
    surprised: "MeiYan",
  },
  mao: {
    idle: { group: "Idle" },
    nod: { group: "", index: 0 }, // mtn_02
    shake: { group: "", index: 1 }, // mtn_03
    thinking: { group: "", index: 2 }, // mtn_04
    look_side: { group: "", index: 3 }, // special_01
    excited: { group: "", index: 4 }, // special_02
    sad: { group: "", index: 2 }, // fallback to mtn_04
    surprised: { group: "", index: 5 }, // special_03
  },
  hiyori: {
    idle: { group: "Idle", index: 0 }, // hiyori_m01
    nod: { group: "Flick", index: 0 }, // hiyori_m03 (wave hand)
    shake: { group: "Flick@Body", index: 0 }, // hiyori_m08 (shake body/head)
    thinking: { group: "Tap@Body", index: 0 }, // hiyori_m07 (thinking/puzzled)
    look_side: { group: "Idle", index: 2 }, // hiyori_m05 (long idle/sway)
    excited: { group: "Idle", index: 1 }, // hiyori_m02 (blush/happy body sway)
    sad: { group: "FlickDown", index: 0 }, // hiyori_m04 (apologetic / sad)
    surprised: { group: "Tap@Body", index: 0 }, // hiyori_m07
  },
  huohuo: {
    idle: "Scene1",
    nod: "haoqi",
    shake: "yaotou",
    thinking: "keshui",
    look_side: "keshui",
    excited: "linghun",
    sad: "yaotou",
    surprised: "linghun",
    zhentou: "zhentou",
  },
};

const VALID_CSS_MOTIONS = new Set([
  "idle",
  "nod",
  "shake",
  "thinking",
  "look_side",
  "excited",
  "sad",
  "surprised",
]);

const EMOTION_TO_MOTION = {
  happy: "excited",
  smile: "nod",
  excited: "excited",
  thinking: "thinking",
  focused: "thinking",
  sad: "sad",
  angry: "shake",
  surprised: "surprised",
  normal: "idle",
  calm: "idle",
  wink: "nod",
  greeting: "nod",
  focus: "thinking",
};

export function normalizeMotion(raw = "idle") {
  const key = (raw || "idle").toLowerCase().trim();
  if (VALID_CSS_MOTIONS.has(key)) return key;
  return EMOTION_TO_MOTION[key] || "idle";
}

export function getMotionForEmotion(emotion = "normal") {
  const key = (emotion || "normal").toLowerCase().trim();
  return EMOTION_TO_MOTION[key] || "idle";
}
