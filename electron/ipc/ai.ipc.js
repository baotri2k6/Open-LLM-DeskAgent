const http = require('http');

const API_HOST = '127.0.0.1';
const API_PORT = 8765;

let targetWindows = [];

function liveTargets() {
  return targetWindows.filter(win => win && !win.isDestroyed());
}

function sendToTargets(channel, payload) {
  for (const win of liveTargets()) {
    win.webContents.send(channel, payload);
  }
}

function requestJSON(method, path, payload = null) {
  return new Promise((resolve, reject) => {
    const body = payload ? JSON.stringify(payload) : null;
    const req = http.request(
      {
        hostname: API_HOST,
        port: API_PORT,
        path,
        method,
        headers: {
          Accept: 'application/json',
          ...(body
            ? {
                'Content-Type': 'application/json; charset=utf-8',
                'Content-Length': Buffer.byteLength(body),
              }
            : {}),
        },
        timeout: 30000,
      },
      res => {
        const chunks = [];
        res.on('data', chunk => chunks.push(chunk));
        res.on('end', () => {
          const raw = Buffer.concat(chunks).toString('utf8');
          let data = {};
          try {
            data = raw ? JSON.parse(raw) : {};
          } catch {
            data = { raw };
          }

          if (res.statusCode >= 200 && res.statusCode < 300) {
            resolve(data);
          } else {
            reject(new Error(data.message || data.error || `HTTP ${res.statusCode}`));
          }
        });
      }
    );

    req.on('timeout', () => req.destroy(new Error('request timeout')));
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

function requestStream(method, path, payload, onChunk, onDone, onError) {
  const body = payload ? JSON.stringify(payload) : null;
  const req = http.request(
    {
      hostname: API_HOST,
      port: API_PORT,
      path,
      method,
      headers: {
        Accept: 'application/json',
        ...(body
          ? {
              'Content-Type': 'application/json; charset=utf-8',
              'Content-Length': Buffer.byteLength(body),
            }
          : {}),
      },
      timeout: 30000,
    },
    res => {
      let buffer = '';
      res.on('data', chunk => {
        buffer += chunk.toString('utf8');
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep last partial line
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          try {
            const data = JSON.parse(trimmed);
            onChunk(data);
          } catch (err) {
            console.error('[electron] error parsing stream chunk:', err, trimmed);
          }
        }
      });
      res.on('end', () => {
        if (buffer.trim()) {
          try {
            const data = JSON.parse(buffer.trim());
            onChunk(data);
          } catch (err) {
            // ignore
          }
        }
        onDone();
      });
    }
  );

  req.on('timeout', () => req.destroy(new Error('request timeout')));
  req.on('error', onError);
  if (body) req.write(body);
  req.end();
}

function sendAvatarState(response) {
  const avatar = response?.avatar || {};
  const expression = avatar.expression || response?.emotion;
  if (expression) sendToTargets('set:emotion', expression);
  if (typeof avatar.lipsync === 'boolean') {
    sendToTargets('set:lipsync', avatar.lipsync);
  }
}

function emitAssistantResponse(response) {
  sendAvatarState(response);
  const text = response?.text || response?.message || '';
  if (text) sendToTargets('chat:chunk', text);
  if (response?.audio_url) {
    sendToTargets('tts:audio', {
      url: response.audio_url,
      duration_ms: response.duration_ms || 0,
    });
  }
  sendToTargets('chat:done', text);
  if (!response?.audio_url) sendToTargets('set:lipsync', false);
}

function audioBase64ToByteArray(audioB64) {
  return Array.from(Buffer.from(audioB64, 'base64'));
}

function registerAiIpc(ipcMain, windows) {
  targetWindows = Array.isArray(windows) ? windows : [windows];

  ipcMain.handle('ai:health', async () => {
    try {
      await requestJSON('GET', '/health');
      sendToTargets('python:ready');
      return { status: 'ok' };
    } catch (err) {
      return { status: 'offline', error: err.message };
    }
  });

  ipcMain.handle('ai:chat', async (_e, { text, image, context }) => {
    return new Promise((resolve) => {
      let fullText = '';
      let audioUrl = null;
      let durationMs = 0;

      requestStream(
        'POST',
        '/chat',
        { text, image, context },
        chunk => {
          if (chunk.type === 'start') {
            sendToTargets('set:emotion', chunk.emotion || 'normal');
            if (chunk.motion) sendToTargets('set:lipsync', chunk.motion === 'thinking');
          } else if (chunk.type === 'request_approval') {
            sendToTargets('chat:request-approval', {
              req_id: chunk.req_id,
              action: chunk.action,
              details: chunk.details
            });
          } else if (chunk.type === 'text') {
            sendToTargets('chat:chunk', chunk.text);
            fullText += chunk.text;
          } else if (chunk.type === 'emotion') {
            if (chunk.emotion) sendToTargets('set:emotion', chunk.emotion);
          } else if (chunk.type === 'command') {
            sendToTargets('chat:command', chunk.command);
          } else if (chunk.type === 'audio') {
            sendToTargets('tts:audio', {
              url: chunk.audio_url,
              duration_ms: chunk.duration_ms || 0,
            });
          } else if (chunk.type === 'done') {
            audioUrl = chunk.audio_url;
            durationMs = chunk.duration_ms;
            if (chunk.emotion) sendToTargets('set:emotion', chunk.emotion);
          }
        },
        () => {
          if (audioUrl) {
            sendToTargets('tts:audio', {
              url: audioUrl,
              duration_ms: durationMs || 0,
            });
          } else {
            sendToTargets('set:lipsync', false);
          }
          sendToTargets('chat:done', fullText);
          resolve({ ok: true, response: { text: fullText, audio_url: audioUrl } });
        },
        err => {
          console.error('[electron] stream error:', err);
          sendToTargets('chat:done', `Có lỗi xảy ra: ${err.message}`);
          resolve({ ok: false, error: err.message });
        }
      );
    });
  });

  ipcMain.handle('ai:voice-input', async (_e, { audio_b64, is_draft, sequence, timestamp }) => {
    try {
      const response = await requestJSON('POST', '/voice/transcribe', {
        audio_bytes: audioBase64ToByteArray(audio_b64),
        mime_type: 'audio/wav',
        is_draft,
        sequence,
        timestamp,
      });
      if (response.success && !is_draft) {
        sendToTargets('stt:result', response.text);
      }
      return { ok: response.success, response };
    } catch (err) {
      return { ok: false, error: err.message };
    }
  });

  ipcMain.handle('ai:cancel-chat', async () => {
    try {
      const response = await requestJSON('POST', '/chat/cancel', {});
      return { ok: true, response };
    } catch (err) {
      return { ok: false, error: err.message };
    }
  });

  ipcMain.handle('ai:load-doc', async (_e, { path: p }) => {
    try {
      const response = await requestJSON('POST', '/documents/import', { path: p });
      sendToTargets('doc:loaded', response);
      return { ok: response.success !== false, response };
    } catch (err) {
      return { ok: false, error: err.message };
    }
  });

  ipcMain.handle('ai:screenshot', async (_e, { question }) => {
    try {
      const response = await requestJSON('POST', '/chat', {
        text: question || 'Nhin man hinh va mo ta noi dung dang hien thi.',
        context: {},
      });
      emitAssistantResponse(response);
      return { ok: true, response };
    } catch (err) {
      return { ok: false, error: err.message };
    }
  });

  ipcMain.handle('ai:get-config', async () => {
    try {
      const response = await requestJSON('GET', '/config');
      return response;
    } catch (err) {
      return { error: err.message };
    }
  });

  ipcMain.handle('ai:get-notifications', async () => {
    try {
      const response = await requestJSON('GET', '/notifications');
      return response;
    } catch (err) {
      return { error: err.message };
    }
  });

  ipcMain.handle('ai:update-config', async (_e, { key, value }) => {
    try {
      const response = await requestJSON('POST', '/config/update', { key, value });
      sendToTargets('config:updated', { key, value });
      return response;
    } catch (err) {
      return { error: err.message };
    }
  });

  ipcMain.handle('ai:interact', async () => {
    try {
      const response = await requestJSON('POST', '/interact');
      return response;
    } catch (err) {
      return { error: err.message };
    }
  });

  ipcMain.handle('ai:submit-approval', async (_e, { req_id, approved }) => {
    try {
      const response = await requestJSON('POST', '/chat/approve', { req_id, approved });
      return response;
    } catch (err) {
      return { error: err.message };
    }
  });
}

module.exports = { registerAiIpc };
