export function renderMessage({ role, text }) {
  const wrap = document.createElement('div');
  wrap.className = `msg msg-${role}`;

  const label = document.createElement('div');
  label.className = 'msg-label';
  label.textContent = role === 'user' ? 'Ban' : (role === 'system' ? 'Hệ thống' : 'IceGirl');

  const body = document.createElement('div');
  body.className = 'msg-body';
  body.textContent = text;

  wrap.append(label, body);
  return wrap;
}

export function renderChunk() {
  const wrap = document.createElement('div');
  wrap.className = 'msg msg-assistant';

  const label = document.createElement('div');
  label.className = 'msg-label';
  label.textContent = 'IceGirl';

  const body = document.createElement('div');
  body.className = 'msg-body';

  wrap.append(label, body);
  return wrap;
}
