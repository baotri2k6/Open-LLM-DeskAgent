const http = require('http');
const { BrowserWindow } = require('electron');
const { broadcast } = require('../websocket-server');

const API_HOST = '127.0.0.1';
const API_PORT = 8765;

function liveTargets() {
  return BrowserWindow.getAllWindows().filter(win => win && !win.isDestroyed());
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

function setLipsync(active) {
  sendToTargets('set:lipsync', active);
  broadcast('lipsync', active);
}

function setEmotion(emotion) {
  sendToTargets('set:emotion', emotion);
  broadcast('emotion', emotion);
}

function sendAvatarState(response) {
  const avatar = response?.avatar || {};
  const expression = avatar.expression || response?.emotion;
  if (expression) setEmotion(expression);
  if (typeof avatar.lipsync === 'boolean') {
    setLipsync(avatar.lipsync);
  }
}

function emitAssistantResponse(response) {
  sendAvatarState(response);
  const text = response?.text || response?.message || '';
  if (text) {
    sendToTargets('chat:chunk', text);
    broadcast('chat_chunk', text);
  }
  if (response?.audio_url) {
    sendToTargets('tts:audio', {
      url: response.audio_url,
      duration_ms: response.duration_ms || 0,
    });
    broadcast('tts_audio', {
      url: response.audio_url,
      duration_ms: response.duration_ms || 0,
    });
  }
  sendToTargets('chat:done', text);
  broadcast('chat_done', text);
  if (!response?.audio_url) setLipsync(false);
}

function audioBase64ToByteArray(audioB64) {
  return Array.from(Buffer.from(audioB64, 'base64'));
}

function registerAiIpc(ipcMain, windows) {
  // windows parameter kept for compatibility

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
            setEmotion(chunk.emotion || 'normal');
            if (chunk.motion) setLipsync(chunk.motion === 'thinking');
            broadcast('start', { emotion: chunk.emotion || 'normal', motion: chunk.motion });
          } else if (chunk.type === 'request_approval') {
            sendToTargets('chat:request-approval', {
              req_id: chunk.req_id,
              action: chunk.action,
              details: chunk.details
            });
          } else if (chunk.type === 'text') {
            if (chunk.thought) {
              sendToTargets('chat:thought-chunk', chunk.text);
              broadcast('thought_chunk', chunk.text);
            } else {
              sendToTargets('chat:chunk', chunk.text);
              fullText += chunk.text;
              broadcast('chat_chunk', chunk.text);
            }
          } else if (chunk.type === 'emotion') {
            if (chunk.emotion) setEmotion(chunk.emotion);
          } else if (chunk.type === 'command') {
            sendToTargets('chat:command', chunk.command);
          } else if (chunk.type === 'audio') {
            sendToTargets('tts:audio', {
              url: chunk.audio_url,
              duration_ms: chunk.duration_ms || 0,
            });
            broadcast('tts_audio', {
              url: chunk.audio_url,
              duration_ms: chunk.duration_ms || 0,
            });
          } else if (chunk.type === 'done') {
            audioUrl = chunk.audio_url;
            durationMs = chunk.duration_ms;
            if (chunk.emotion) setEmotion(chunk.emotion);
          }
        },
        () => {
          if (audioUrl) {
            sendToTargets('tts:audio', {
              url: audioUrl,
              duration_ms: durationMs || 0,
            });
            broadcast('tts_audio', {
              url: audioUrl,
              duration_ms: durationMs || 0,
            });
          } else {
            setLipsync(false);
          }
          sendToTargets('chat:done', fullText);
          broadcast('chat_done', fullText);
          resolve({ ok: true, response: { text: fullText, audio_url: audioUrl } });
        },
        err => {
          console.error('[electron] stream error:', err);
          sendToTargets('chat:done', `Có lỗi xảy ra: ${err.message}`);
          broadcast('chat_done', `Có lỗi xảy ra: ${err.message}`);
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

  ipcMain.handle('ai:get-memories', async () => {
    try {
      const response = await requestJSON('GET', '/memories');
      return response;
    } catch (err) {
      return { error: err.message };
    }
  });

  ipcMain.handle('ai:update-memory', async (_e, { id, text }) => {
    try {
      const response = await requestJSON('POST', '/memories/update', { id, text });
      return response;
    } catch (err) {
      return { error: err.message };
    }
  });

  ipcMain.handle('ai:delete-memory', async (_e, { id }) => {
    try {
      const response = await requestJSON('POST', '/memories/delete', { id });
      return response;
    } catch (err) {
      return { error: err.message };
    }
  });

  ipcMain.handle('ai:add-memory', async (_e, { text }) => {
    try {
      const response = await requestJSON('POST', '/memories/add', { text });
      return response;
    } catch (err) {
      return { error: err.message };
    }
  });

  ipcMain.handle('ai:tts', async (_e, { text }) => {
    try {
      const response = await requestJSON('POST', '/voice/tts', { text });
      return { ok: response.success !== false, response };
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

      if (key === 'app.avatarScale') {
        const scale = parseFloat(value) || 1.0;
        const AVATAR_WINDOW_WIDTH = 420;
        const AVATAR_WINDOW_HEIGHT = 640;
        const avatarWin = BrowserWindow.getAllWindows().find(win => {
          try {
            return win.webContents.getURL().includes('avatar.html');
          } catch {
            return false;
          }
        });
        if (avatarWin && !avatarWin.isDestroyed()) {
          const newW = Math.round(AVATAR_WINDOW_WIDTH * scale);
          const newH = Math.round(AVATAR_WINDOW_HEIGHT * scale);
          const [curX, curY] = avatarWin.getPosition();
          const [curW, curH] = avatarWin.getSize();
          const newX = curX + curW - newW;
          const newY = curY + curH - newH;
          
          const wasResizable = avatarWin.isResizable();
          avatarWin.setResizable(true);
          avatarWin.setSize(newW, newH);
          avatarWin.setPosition(newX, newY);
          avatarWin.setResizable(wasResizable);
        }
      }

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

  ipcMain.on('ai:broadcast', (_e, { event, data }) => {
    broadcast(event, data);
  });
}

module.exports = { registerAiIpc };
