// Stream Chat Widget controller logic for AIRI Live
const chatLog = document.getElementById("chatLog") as HTMLDivElement;
const chatForm = document.getElementById("chatForm") as HTMLFormElement;
const chatInput = document.getElementById("chatInput") as HTMLInputElement;
const btnMinimize = document.getElementById("btnMinimize");
const btnClose = document.getElementById("btnClose");

// RAG / Plan progress elements
const checklistArea = document.getElementById("checklistArea") as HTMLDivElement;
const checklistItems = document.getElementById("checklistItems") as HTMLUListElement;

let currentBotMessageEl: HTMLDivElement | null = null;
let currentBotTextEl: HTMLParagraphElement | null = null;
let currentBotText = "";

// Append message helper
function appendMessage(role: "user" | "bot", text: string): void {
  const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  const isUser = role === "user";
  
  const msgEl = document.createElement("div");
  // Staggered: user on the right, bot on the left
  msgEl.className = "flex flex-col gap-1 p-3.5 max-w-[80%] transition duration-200 " + 
                    (isUser 
                      ? "self-end text-right message-glass-user" 
                      : "self-start text-left message-glass-bot");
  
  const headerEl = document.createElement("div");
  headerEl.className = "flex items-center gap-1.5 text-[9px] font-bold tracking-wider " + 
                       (isUser ? "justify-end text-sky-700/60" : "justify-start text-slate-500/60");
  
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

// Stream chunk helper
function appendChunk(chunk: string): void {
  if (!currentBotTextEl) {
    appendMessage("bot", chunk);
  } else {
    currentBotText += chunk;
    currentBotTextEl.textContent = currentBotText;
    chatLog.scrollTop = chatLog.scrollHeight;
  }
}

// Window controllers
btnMinimize?.addEventListener("click", () => {
  (window as any).companion?.invoke("win:minimize-chat").catch(() => null);
});

btnClose?.addEventListener("click", () => {
  (window as any).companion?.invoke("win:close-chat").catch(() => null);
});

// Chat submit action
chatForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const text = chatInput.value.trim();
  if (!text) return;
  
  chatInput.value = "";
  appendMessage("user", text);
  
  // Clear bot reference to start fresh for response stream
  currentBotMessageEl = null;
  currentBotTextEl = null;
  currentBotText = "";
  
  chatInput.disabled = true;
  const submitBtn = chatForm.querySelector("button[type='submit']") as HTMLButtonElement | null;
  if (submitBtn) submitBtn.disabled = true;
  
  try {
    await (window as any).companion.invoke("ai:chat", { text });
  } catch (err: any) {
    console.error("Chat error:", err);
    appendMessage("bot", `Lỗi kết nối: ${err.message}. Cậu kiểm tra lại nhé.`);
  } finally {
    chatInput.disabled = false;
    if (submitBtn) submitBtn.disabled = false;
    chatInput.focus();
  }
});

// Listeners for IPC events
if ((window as any).companion) {
  // Listen for stream chunks from server
  (window as any).companion.on("chat:chunk", (chunk: string) => {
    appendChunk(chunk);
  });
  
  // Listen for finished responses
  (window as any).companion.on("chat:done", () => {
    currentBotMessageEl = null;
    currentBotTextEl = null;
    currentBotText = "";
    chatInput.disabled = false;
    const submitBtn = chatForm.querySelector("button[type='submit']") as HTMLButtonElement | null;
    if (submitBtn) submitBtn.disabled = false;
    chatInput.focus();
  });

  // Listen for checklist and planning progress notifications
  (window as any).companion.on("python:ready", () => {
    console.log("Python backend is ready inside overlay chat window.");
  });

  // Load previous messages / greet
  setTimeout(() => {
    appendMessage("bot", "DeskAgent đã sẵn sàng kết nối live! Chào cậu nha! [smile]");
  }, 500);

  // Poll for planner / developer workflow notifications
  setInterval(async () => {
    try {
      const res = await (window as any).companion.invoke("ai:get-notifications", "coding");
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
            updateStepStatus(idx, 'in_progress');
          } else if (type === "PlanStepFinished") {
            const idx = payload?.step_index;
            const success = payload?.success;
            updateStepStatus(idx, success ? 'done' : 'failed');
          } else if (type === "PlanFinished") {
            const items = checklistItems?.querySelectorAll("li");
            items?.forEach(item => {
              item.style.textDecoration = "line-through";
              item.style.color = "#ccff00";
            });
            setTimeout(() => {
              checklistArea?.classList.add("hidden");
            }, 6000);
          }
        }
      }
    } catch (e) {
      // quiet fail
    }
  }, 2000);
}

function renderTaskChecklist(steps: any[]): void {
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

function updateStepStatus(idx: number, status: 'pending' | 'in_progress' | 'done' | 'failed'): void {
  const item = document.getElementById(`chat-step-${idx}`);
  if (!item) return;
  
  const indicator = item.querySelector(".status-indicator") as HTMLSpanElement | null;
  const text = item.querySelector(".step-text") as HTMLSpanElement | null;
  if (!indicator || !text) return;
  
  if (status === 'in_progress') {
    indicator.className = "status-indicator w-2 h-2 rounded-full bg-[#00f0ff] animate-pulse";
    text.className = "step-text text-white font-semibold";
  } else if (status === 'done') {
    indicator.className = "status-indicator w-2 h-2 rounded-full bg-[#ccff00]";
    text.className = "step-text text-zinc-500 line-through";
  } else if (status === 'failed') {
    indicator.className = "status-indicator w-2 h-2 rounded-full bg-red-600";
    text.className = "step-text text-red-400 font-bold";
  }
}
