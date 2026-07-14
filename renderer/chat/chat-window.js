const chatLog = document.getElementById("chatLog");
const chatForm = document.getElementById("chatForm");
const chatInput = document.getElementById("chatInput");
const btnMinimize = document.getElementById("btnMinimize");
const btnClose = document.getElementById("btnClose");
const checklistArea = document.getElementById("checklistArea");
const checklistItems = document.getElementById("checklistItems");
let currentBotMessageEl = null;
let currentBotTextEl = null;
let currentBotText = "";
function appendMessage(role, text) {
  const time = (/* @__PURE__ */ new Date()).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const isUser = role === "user";
  const msgEl = document.createElement("div");
  msgEl.className = "flex flex-col gap-1 p-3.5 max-w-[80%] transition duration-200 " + (isUser ? "self-end text-right message-glass-user" : "self-start text-left message-glass-bot");
  const headerEl = document.createElement("div");
  headerEl.className = "flex items-center gap-1.5 text-[9px] font-bold tracking-wider " + (isUser ? "justify-end text-sky-700/60" : "justify-start text-slate-500/60");
  const tagEl = document.createElement("span");
  tagEl.textContent = isUser ? "YOU" : "DESKAGENT";
  const timeEl = document.createElement("span");
  timeEl.className = "opacity-75";
  timeEl.textContent = time;
  if (isUser) {
    headerEl.appendChild(timeEl);
    headerEl.appendChild(tagEl);
  } else {
    headerEl.appendChild(tagEl);
    headerEl.appendChild(timeEl);
  }
  msgEl.appendChild(headerEl);
  const textEl = document.createElement("p");
  textEl.className = "text-xs leading-relaxed break-words font-medium " + (isUser ? "text-sky-900" : "text-slate-800");
  textEl.textContent = text;
  msgEl.appendChild(textEl);
  chatLog.appendChild(msgEl);
  chatLog.scrollTop = chatLog.scrollHeight;
  if (role === "bot") {
    currentBotMessageEl = msgEl;
    currentBotTextEl = textEl;
    currentBotText = text;
  }
}
function appendChunk(chunk) {
  if (!currentBotTextEl) {
    appendMessage("bot", chunk);
  } else {
    currentBotText += chunk;
    currentBotTextEl.textContent = currentBotText;
    chatLog.scrollTop = chatLog.scrollHeight;
  }
}
btnMinimize?.addEventListener("click", () => {
  window.companion?.invoke("win:minimize-chat").catch(() => null);
});
btnClose?.addEventListener("click", () => {
  window.companion?.invoke("win:close-chat").catch(() => null);
});
chatForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  chatInput.value = "";
  appendMessage("user", text);
  currentBotMessageEl = null;
  currentBotTextEl = null;
  currentBotText = "";
  chatInput.disabled = true;
  const submitBtn = chatForm.querySelector("button[type='submit']");
  if (submitBtn) submitBtn.disabled = true;
  try {
    await window.companion.invoke("ai:chat", { text });
  } catch (err) {
    console.error("Chat error:", err);
    appendMessage("bot", `L\u1ED7i k\u1EBFt n\u1ED1i: ${err.message}. C\u1EADu ki\u1EC3m tra l\u1EA1i nh\xE9.`);
  } finally {
    chatInput.disabled = false;
    if (submitBtn) submitBtn.disabled = false;
    chatInput.focus();
  }
});
if (window.companion) {
  window.companion.on("chat:chunk", (chunk) => {
    appendChunk(chunk);
  });
  window.companion.on("chat:done", () => {
    currentBotMessageEl = null;
    currentBotTextEl = null;
    currentBotText = "";
    chatInput.disabled = false;
    const submitBtn = chatForm.querySelector("button[type='submit']");
    if (submitBtn) submitBtn.disabled = false;
    chatInput.focus();
  });
  window.companion.on("python:ready", () => {
    console.log("Python backend is ready inside overlay chat window.");
  });
  setTimeout(() => {
    appendMessage("bot", "DeskAgent \u0111\xE3 s\u1EB5n s\xE0ng k\u1EBFt n\u1ED1i live! Ch\xE0o c\u1EADu nha! [smile]");
  }, 500);
  setInterval(async () => {
    try {
      const res = await window.companion.invoke("ai:get-notifications", "coding");
      if (res && res.notifications && res.notifications.length > 0) {
        for (const note of res.notifications) {
          const type = note.event_type;
          const payload = note.payload;
          if (!type) continue;
          if (type === "PlanCreated") {
            const steps = payload?.steps ?? [];
            renderTaskChecklist(steps);
          } else if (type === "PlanStepStarted") {
            const idx = payload?.step_index;
            updateStepStatus(idx, "in_progress");
          } else if (type === "PlanStepFinished") {
            const idx = payload?.step_index;
            const success = payload?.success;
            updateStepStatus(idx, success ? "done" : "failed");
          } else if (type === "PlanFinished") {
            const items = checklistItems?.querySelectorAll("li");
            items?.forEach((item) => {
              item.style.textDecoration = "line-through";
              item.style.color = "#ccff00";
            });
            setTimeout(() => {
              checklistArea?.classList.add("hidden");
            }, 6e3);
          }
        }
      }
    } catch (e) {
    }
  }, 2e3);
}
function renderTaskChecklist(steps) {
  if (!checklistArea || !checklistItems) return;
  checklistItems.innerHTML = "";
  steps.forEach((step, idx) => {
    const li = document.createElement("li");
    li.id = `chat-step-${idx}`;
    li.className = "flex items-center gap-1.5 text-zinc-300";
    li.innerHTML = `
      <span class="status-indicator w-2 h-2 rounded-full bg-zinc-600"></span>
      <span class="step-text">${step.description}</span>
    `;
    checklistItems.appendChild(li);
  });
  checklistArea.classList.remove("hidden");
  chatLog.scrollTop = chatLog.scrollHeight;
}
function updateStepStatus(idx, status) {
  const item = document.getElementById(`chat-step-${idx}`);
  if (!item) return;
  const indicator = item.querySelector(".status-indicator");
  const text = item.querySelector(".step-text");
  if (!indicator || !text) return;
  if (status === "in_progress") {
    indicator.className = "status-indicator w-2 h-2 rounded-full bg-[#00f0ff] animate-pulse";
    text.className = "step-text text-white font-semibold";
  } else if (status === "done") {
    indicator.className = "status-indicator w-2 h-2 rounded-full bg-[#ccff00]";
    text.className = "step-text text-zinc-500 line-through";
  } else if (status === "failed") {
    indicator.className = "status-indicator w-2 h-2 rounded-full bg-red-600";
    text.className = "step-text text-red-400 font-bold";
  }
}
