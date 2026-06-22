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

export function renderApprovalCard(req_id, action, details) {
  const wrap = document.createElement('div');
  wrap.className = 'msg msg-assistant msg-approval';

  const label = document.createElement('div');
  label.className = 'msg-label';
  label.textContent = 'Hệ thống - Chờ duyệt';

  const body = document.createElement('div');
  body.className = 'msg-body';

  const title = document.createElement('div');
  title.style.fontWeight = 'bold';
  title.style.marginBottom = '8px';
  title.textContent = `IceGirl yêu cầu thực hiện hành động: "${action}"`;
  body.appendChild(title);

  const detailBox = document.createElement('pre');
  detailBox.className = 'approval-details';
  detailBox.style.background = 'rgba(0, 0, 0, 0.2)';
  detailBox.style.padding = '8px';
  detailBox.style.borderRadius = '4px';
  detailBox.style.overflowX = 'auto';
  detailBox.style.fontFamily = 'monospace';
  detailBox.style.fontSize = '12px';
  detailBox.style.whiteSpace = 'pre-wrap';
  detailBox.style.wordBreak = 'break-all';
  
  if (action === 'execute_command') {
    detailBox.textContent = `Lệnh: ${details.command}`;
  } else if (action === 'write_to_file') {
    detailBox.textContent = `File: ${details.path}\nNội dung (một phần):\n${details.content.slice(0, 400)}`;
  } else {
    detailBox.textContent = JSON.stringify(details, null, 2);
  }
  body.appendChild(detailBox);

  const btnRow = document.createElement('div');
  btnRow.className = 'approval-buttons';
  btnRow.style.display = 'flex';
  btnRow.style.gap = '8px';
  btnRow.style.marginTop = '12px';

  const btnAllow = document.createElement('button');
  btnAllow.className = 'btn-allow';
  btnAllow.textContent = 'Cho phép';
  btnAllow.style.background = '#2ecc71';
  btnAllow.style.color = '#fff';
  btnAllow.style.border = 'none';
  btnAllow.style.padding = '6px 12px';
  btnAllow.style.borderRadius = '4px';
  btnAllow.style.cursor = 'pointer';

  const btnDeny = document.createElement('button');
  btnDeny.className = 'btn-deny';
  btnDeny.textContent = 'Từ chối';
  btnDeny.style.background = '#e74c3c';
  btnDeny.style.color = '#fff';
  btnDeny.style.border = 'none';
  btnDeny.style.padding = '6px 12px';
  btnDeny.style.borderRadius = '4px';
  btnDeny.style.cursor = 'pointer';

  btnRow.append(btnAllow, btnDeny);
  body.appendChild(btnRow);

  const handleChoice = async (approved) => {
    btnAllow.disabled = true;
    btnDeny.disabled = true;
    btnAllow.style.opacity = 0.5;
    btnDeny.style.opacity = 0.5;
    btnAllow.style.cursor = 'default';
    btnDeny.style.cursor = 'default';
    
    if (approved) {
      btnAllow.style.opacity = 1;
      btnAllow.textContent = 'Đã cho phép';
      btnDeny.style.display = 'none';
    } else {
      btnDeny.style.opacity = 1;
      btnDeny.textContent = 'Đã từ chối';
      btnAllow.style.display = 'none';
    }
    
    await window.companion.invoke('ai:submit-approval', { req_id, approved });
  };

  btnAllow.addEventListener('click', () => handleChoice(true));
  btnDeny.addEventListener('click', () => handleChoice(false));

  wrap.append(label, body);
  return wrap;
}

