const { WebSocketServer } = require("ws");

let wss = null;
const clients = new Set();

function startWebSocketServer(port = 9001) {
  if (wss) return wss;

  try {
    wss = new WebSocketServer({ port });
    console.log(`[websocket-server] Server running on ws://127.0.0.1:${port}`);

    wss.on("connection", (ws) => {
      console.log("[websocket-server] New OBS client connected");
      clients.add(ws);

      // Send a welcome event to verify the connection
      ws.send(JSON.stringify({ event: "connected", data: { status: "ready" } }));

      ws.on("close", () => {
        console.log("[websocket-server] OBS client disconnected");
        clients.delete(ws);
      });

      ws.on("error", (err) => {
        console.error("[websocket-server] Connection error:", err);
        clients.delete(ws);
      });
    });
  } catch (err) {
    console.error("[websocket-server] Failed to start server:", err);
  }

  return wss;
}

function broadcast(event, data) {
  const payload = JSON.stringify({ event, data });
  for (const client of clients) {
    if (client.readyState === 1) { // 1 = OPEN
      try {
        client.send(payload);
      } catch (err) {
        console.error("[websocket-server] Error broadcasting to client:", err);
      }
    }
  }
}

module.exports = {
  startWebSocketServer,
  broadcast,
};
