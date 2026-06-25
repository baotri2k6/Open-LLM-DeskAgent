const WS_PORT = 9001;
const IDLE_TIMEOUT_MS = 5000;

let socket = null;
let idleTimer = null;

// DOM Elements
const statusBadge = document.getElementById("statusBadge");
const statusText = document.getElementById("statusText");
const thoughtBubble = document.getElementById("thoughtBubble");
const thoughtContent = document.getElementById("thoughtContent");
const speechBubble = document.getElementById("speechBubble");
const speechContent = document.getElementById("speechContent");

function initWebSocket() {
  console.log(`Connecting to ws://127.0.0.1:${WS_PORT}...`);
  socket = new WebSocket(`ws://127.0.0.1:${WS_PORT}`);

  socket.onopen = () => {
    console.log("Connected to DeskAgent WebSocket server");
    updateStatus("connected", "Sẵn sàng");
    setTimeout(() => {
      statusBadge.classList.add("hidden");
    }, 2000);
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      handleEvent(data.event, data.data);
    } catch (err) {
      console.error("Error parsing WebSocket message:", err);
    }
  };

  socket.onclose = () => {
    console.warn("WebSocket connection closed. Reconnecting in 3s...");
    updateStatus("disconnected", "Mất kết nối");
    statusBadge.classList.remove("hidden");
    hideAllBubbles();
    setTimeout(initWebSocket, 3000);
  };

  socket.onerror = (err) => {
    console.error("WebSocket error:", err);
    socket.close();
  };
}

function handleEvent(event, data) {
  // Clear any active idle timers when a new event arrives
  if (idleTimer) {
    clearTimeout(idleTimer);
    idleTimer = null;
  }

  switch (event) {
    case "start":
      hideAllBubbles();
      speechContent.textContent = "";
      thoughtContent.textContent = "";
      
      statusBadge.classList.remove("hidden");
      if (data.motion === "thinking") {
        updateStatus("thinking", "Đang suy nghĩ...");
      } else {
        updateStatus("speaking", "Đang nói...");
      }
      break;

    case "thought_chunk":
      updateStatus("thinking", "Đang suy nghĩ...");
      statusBadge.classList.remove("hidden");
      
      thoughtBubble.classList.remove("hidden");
      thoughtContent.textContent += data;
      break;

    case "chat_chunk":
      updateStatus("speaking", "Đang trả lời...");
      statusBadge.classList.remove("hidden");
      
      // Hide thought bubble when it starts speaking
      thoughtBubble.classList.add("hidden");
      
      speechBubble.classList.remove("hidden");
      speechContent.textContent += data;
      break;

    case "lipsync":
      if (data) {
        updateStatus("speaking", "Đang nói...");
      } else {
        if (!speechBubble.classList.contains("hidden")) {
          updateStatus("connected", "Sẵn sàng");
        }
      }
      break;

    case "emotion":
      console.log("Emotion changed to:", data);
      break;

    case "chat_done":
      updateStatus("connected", "Sẵn sàng");
      
      // Set idle timer to auto-hide bubbles after 5 seconds
      idleTimer = setTimeout(() => {
        hideAllBubbles();
        statusBadge.classList.add("hidden");
      }, IDLE_TIMEOUT_MS);
      break;
      
    default:
      console.log("Unhandled event:", event, data);
  }
}

function updateStatus(mode, text) {
  statusBadge.className = "status-badge";
  statusBadge.classList.add(mode);
  statusText.textContent = text;
}

function hideAllBubbles() {
  speechBubble.classList.add("hidden");
  thoughtBubble.classList.add("hidden");
}

// Start WebSocket connection
initWebSocket();
