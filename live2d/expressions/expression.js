/**
 * Semantic emotion names mapped to the IceGirl expression files.
 */

export const EXPRESSION_TO_LIVE2D = {
  normal: null,
  neutral: null,
  smile: '脸红',
  friendly: '脸红',
  happy: '爱心眼',
  excited: '星星眼',
  focused: null,
  thinking: '疑惑',
  sad: '流泪',
  angry: '生气',
  surprised: '惊讶',
  wink: '歪嘴→',
  tongue: '舌头',
  money: '金钱眼',
};

export const EXPRESSION_MAPPINGS = {
  icegirl: {
    normal: null,
    neutral: null,
    smile: '脸红',
    friendly: '脸红',
    happy: '爱心眼',
    excited: '星星眼',
    focused: null,
    thinking: '疑惑',
    sad: '流泪',
    angry: '生气',
    surprised: '惊讶',
    wink: '歪嘴→',
    tongue: '舌头',
    money: '金钱眼',
  },
  mao: {
    normal: 'exp_01',
    neutral: 'exp_01',
    smile: 'exp_02',
    friendly: 'exp_02',
    happy: 'exp_04',
    excited: 'exp_04',
    focused: 'exp_06',
    thinking: 'exp_06',
    sad: 'exp_05',
    angry: 'exp_08',
    surprised: 'exp_07',
    wink: 'exp_02',
    tongue: 'exp_01',
    money: 'exp_04',
  },
  hiyori: {
    normal: null,
    neutral: null,
    smile: null,
    friendly: null,
    happy: null,
    excited: null,
    focused: null,
    thinking: null,
    sad: null,
    angry: null,
    surprised: null,
    wink: null,
    tongue: null,
    money: null,
  },
  huohuo: {
    normal: null,
    neutral: null,
    smile: 'baozhen',
    friendly: 'baozhen',
    happy: 'baozhen',
    excited: 'qizi2',
    focused: 'qizi1',
    thinking: 'baozhen',
    sad: 'cry',
    angry: 'angry',
    surprised: 'white eyes',
    wink: 'baozhen',
    tongue: null,
    money: 'baozhen',
  }
};


const CSS_EXPRESSION_MAP = {
  normal: 'normal',
  neutral: 'normal',
  smile: 'smile',
  friendly: 'smile',
  happy: 'happy',
  excited: 'happy',
  focused: 'focused',
  thinking: 'focused',
  sad: 'sad',
  angry: 'sad',
  surprised: 'surprised',
  wink: 'smile',
  tongue: 'happy',
  money: 'happy',
};

export function normalizeExpression(raw = 'normal') {
  const key = (raw || 'normal').toLowerCase().trim();
  return CSS_EXPRESSION_MAP[key] || 'normal';
}

export function getCSSExpression(key) {
  return CSS_EXPRESSION_MAP[key] ?? 'normal';
}
