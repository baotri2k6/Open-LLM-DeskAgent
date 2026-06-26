/**
 * DeskAgent Coding Console — Script điều khiển giao diện Lập trình tự động.
 */

let currentFolder = null;
let activeTaskRunning = false;
let currentThoughtContainer = null;
let currentThoughtBody = null;

const folderPathDisplay = document.getElementById("folderPathDisplay");
const selectFolderButton = document.getElementById("selectFolderButton");
const fileTreeContainer = document.getElementById("fileTreeContainer");
const fileCount = document.getElementById("fileCount");
const codingChatLog = document.getElementById("codingChatLog");
const codingChatForm = document.getElementById("codingChatForm");
const codingChatInput = document.getElementById("codingChatInput");
const submitTaskButton = document.getElementById("submitTaskButton");
const activeWorkspaceTitle = document.getElementById("activeWorkspaceTitle");
const activeWorkspacePath = document.getElementById("activeWorkspacePath");
const clearChatButton = document.getElementById("clearChatButton");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");

// Initialize Suggestion Buttons
document.querySelectorAll(".suggest-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    codingChatInput.value = btn.textContent.replace(/"/g, "");
    codingChatInput.focus();
  });
});

// Clear Chat History
clearChatButton.addEventListener("click", () => {
  if (confirm("Bạn có chắc chắn muốn xóa lịch sử chat và các báo cáo lập trình hiện tại không?")) {
    codingChatLog.innerHTML = `
      <div class="system-welcome-card">
        <div class="welcome-icon">🚀</div>
        <h2>Coding Agent Sẵn Sàng</h2>
        <p>Nhập yêu cầu sửa lỗi, viết code hoặc tạo tính năng mới ở khung phía dưới. Tôi sẽ quét thư mục dự án, đề xuất thay đổi, tạo diff trực quan và chạy thử nghiệm (testing) để tự sửa lỗi.</p>
        <div class="suggestions-grid">
          <button class="suggest-btn" type="button">"Sửa các lỗi logic trong file main.py"</button>
          <button class="suggest-btn" type="button">"Viết unit test cho hàm tính toán trong utils.py"</button>
          <button class="suggest-btn" type="button">"Thêm phương thức mới để format dữ liệu đầu ra"</button>
        </div>
      </div>
    `;
    
    // Re-bind suggestion clicks
    document.querySelectorAll(".suggest-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        codingChatInput.value = btn.textContent.replace(/"/g, "");
        codingChatInput.focus();
      });
    });
  }
});

// Select folder manually via Electron dialog
selectFolderButton.addEventListener("click", async () => {
  try {
    const selected = await window.companion.invoke("dialog:select-folder");
    if (selected) {
      setWorkspaceFolder(selected);
    }
  } catch (err) {
    console.error("Lỗi khi mở hộp thoại chọn thư mục:", err);
  }
});

// Listen from Electron IPC (when folder is dropped onto the pet window)
window.companion.on("workspace:set-folder", (folderPath) => {
  console.log("[coding] Folder path received from IPC:", folderPath);
  setWorkspaceFolder(folderPath);
});

// Handle drag and drop folder directly onto Coding Console window
document.addEventListener("dragover", (e) => {
  e.preventDefault();
  e.stopPropagation();
});

document.addEventListener("drop", (e) => {
  e.preventDefault();
  e.stopPropagation();
  
  const files = e.dataTransfer.files;
  if (files && files.length > 0) {
    const file = files[0];
    const filePath = file.path; // Electron exposes absolute path
    if (filePath) {
      setWorkspaceFolder(filePath);
    }
  }
});

// Set workspace folder and scan files
async function setWorkspaceFolder(folderPath) {
  currentFolder = folderPath;
  const folderName = folderPath.replace(/\\/g, "/").split("/").pop() || folderPath;
  
  activeWorkspaceTitle.textContent = `Workspace: ${folderName}`;
  activeWorkspacePath.textContent = folderPath;
  folderPathDisplay.textContent = folderPath;
  
  updateAgentStatus("idle", "Đang sẵn sàng");
  
  await scanWorkspaceFiles();
}
// Hoist function
window.setWorkspaceFolder = setWorkspaceFolder;

async function scanWorkspaceFiles() {
  if (!currentFolder) return;
  
  fileTreeContainer.innerHTML = '<div class="empty-state">Đang quét danh sách tệp tin...</div>';
  
  try {
    // Call server endpoint /swe/scan to list files
    const res = await fetch("http://127.0.0.1:8765/swe/scan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ directory: currentFolder })
    });
    
    const data = await res.json();
    if (data.success && data.files) {
      renderFileTree(data.files);
    } else {
      fileTreeContainer.innerHTML = `<div class="empty-state error">Lỗi quét tệp: ${data.error || "Không rõ nguyên nhân"}</div>`;
    }
  } catch (err) {
    fileTreeContainer.innerHTML = `<div class="empty-state error">Không thể kết nối tới Backend server: ${err.message}</div>`;
  }
}

function renderFileTree(files) {
  fileCount.textContent = files.length;
  if (files.length === 0) {
    fileTreeContainer.innerHTML = '<div class="empty-state">Thư mục trống</div>';
    return;
  }
  
  fileTreeContainer.innerHTML = "";
  files.sort().forEach(relPath => {
    const item = document.createElement("div");
    item.className = "file-item";
    
    // Guess icon by extension
    let icon = "📄";
    if (relPath.endsWith(".py")) icon = "🐍";
    else if (relPath.endsWith(".js") || relPath.endsWith(".ts")) icon = "🟨";
    else if (relPath.endsWith(".html")) icon = "🌐";
    else if (relPath.endsWith(".css")) icon = "🎨";
    else if (relPath.endsWith(".json") || relPath.endsWith(".yaml") || relPath.endsWith(".yml")) icon = "⚙️";
    else if (relPath.endsWith(".md")) icon = "📝";
    
    item.innerHTML = `<span class="file-icon">${icon}</span> ${relPath}`;
    item.addEventListener("click", () => {
      document.querySelectorAll(".file-item").forEach(el => el.classList.remove("selected"));
      item.classList.add("selected");
    });
    fileTreeContainer.appendChild(item);
  });
}

function updateAgentStatus(status, text) {
  statusDot.className = `status-dot ${status}`;
  statusText.textContent = text;
}

// Submit Task Form
codingChatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  if (activeTaskRunning) return;
  if (!currentFolder) {
    alert("Vui lòng chọn hoặc thả một thư mục làm việc vào trước khi khởi chạy Coding Agent.");
    return;
  }
  
  const task = codingChatInput.value.trim();
  if (!task) return;
  
  activeTaskRunning = true;
  submitTaskButton.disabled = true;
  codingChatInput.disabled = true;
  updateAgentStatus("running", "Đang phân tích tác vụ...");
  
  // Clear welcome card if it's the first message
  const welcomeCard = codingChatLog.querySelector(".system-welcome-card");
  if (welcomeCard) {
    codingChatLog.innerHTML = "";
  }
  
  // Append user message
  appendUserMessage(task);
  codingChatInput.value = "";
  
  // Start execution stream
  try {
    const response = await fetch("http://127.0.0.1:8765/swe/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt: task, directory: currentFolder })
    });
    
    if (!response.ok) {
      appendStatusTag("Lỗi kết nối tới Backend", "error");
      throw new Error(`Server returned status ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    
    // Clear thought refs
    currentThoughtContainer = null;
    currentThoughtBody = null;
    
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // save remaining partial chunk
      
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;
        try {
          const event = JSON.parse(trimmed);
          handleProgressEvent(event);
        } catch (err) {
          // partial parsing fail, wait for buffer accumulation
        }
      }
    }
    
  } catch (err) {
    console.error("Error in SWE execution:", err);
    appendStatusTag(`Lỗi thực thi Coding Agent: ${err.message}`, "error");
    updateAgentStatus("error", "Lỗi chạy tác vụ");
  } finally {
    activeTaskRunning = false;
    submitTaskButton.disabled = false;
    codingChatInput.disabled = false;
    codingChatInput.focus();
    
    // Refresh folder view to show new files or edits
    await scanWorkspaceFiles();
  }
});

function appendUserMessage(text) {
  const bubble = document.createElement("div");
  bubble.className = "message-bubble user";
  bubble.textContent = text;
  codingChatLog.appendChild(bubble);
  scrollChatToBottom();
}

function handleProgressEvent(event) {
  switch (event.type) {
    case "status":
      appendStatusTag(event.message, "info");
      updateAgentStatus("running", event.message);
      break;
      
    case "iteration":
      appendStatusTag(`--- Chu Kỳ Sửa Lỗi ${event.number} / ${event.max} ---`, "info");
      break;
      
    case "thought_token":
      appendThoughtToken(event.token);
      break;
      
    case "file_changed":
      // Close thought if open
      closeThoughtBox();
      renderDiff(event.path, event.diff);
      break;
      
    case "test_result":
      closeThoughtBox();
      renderTestResult(event);
      break;
      
    case "error":
      closeThoughtBox();
      appendStatusTag(event.message, "error");
      updateAgentStatus("error", event.message);
      break;
      
    case "done":
      closeThoughtBox();
      appendStatusTag(event.message, event.success ? "success" : "error");
      updateAgentStatus(event.success ? "success" : "error", event.success ? "Hoàn thành tác vụ" : "Thất bại");
      break;
  }
}

function appendStatusTag(msg, level) {
  const tag = document.createElement("div");
  tag.className = `progress-status-tag status-${level}`;
  
  let prefix = "ℹ️";
  if (level === "success") prefix = "✅";
  else if (level === "error") prefix = "❌";
  else if (level === "warning") prefix = "⚠️";
  
  tag.textContent = `${prefix} ${msg}`;
  codingChatLog.appendChild(tag);
  scrollChatToBottom();
}

function appendThoughtToken(token) {
  if (!currentThoughtContainer) {
    // Create new thought block
    currentThoughtContainer = document.createElement("div");
    currentThoughtContainer.className = "thought-container";
    
    const header = document.createElement("div");
    header.className = "thought-header";
    header.innerHTML = `<span>💡 Suy nghĩ của Coding Agent (Thought Process)...</span> <span class="toggle-icon">▼</span>`;
    
    currentThoughtBody = document.createElement("div");
    currentThoughtBody.className = "thought-body";
    
    header.addEventListener("click", () => {
      const isHidden = currentThoughtBody.classList.toggle("hidden");
      header.querySelector(".toggle-icon").textContent = isHidden ? "▲" : "▼";
    });
    
    currentThoughtContainer.appendChild(header);
    currentThoughtContainer.appendChild(currentThoughtBody);
    codingChatLog.appendChild(currentThoughtContainer);
  }
  
  // Append token to thought body
  currentThoughtBody.textContent += token;
  scrollChatToBottom();
}

function closeThoughtBox() {
  currentThoughtContainer = null;
  currentThoughtBody = null;
}

function renderDiff(filePath, diffText) {
  if (!diffText || diffText.trim() === "") return;
  
  const container = document.createElement("div");
  container.className = "diff-container";
  
  const header = document.createElement("div");
  header.className = "diff-header";
  header.innerHTML = `<span>✏️ Thay đổi tại tệp: <strong>${filePath}</strong></span> <span class="badge">DIFF</span>`;
  
  const content = document.createElement("div");
  content.className = "diff-content";
  
  const lines = diffText.split("\n");
  lines.forEach(line => {
    const lineEl = document.createElement("div");
    lineEl.className = "diff-line";
    
    if (line.startsWith("+") && !line.startsWith("+++")) {
      lineEl.className += " addition";
    } else if (line.startsWith("-") && !line.startsWith("---")) {
      lineEl.className += " deletion";
    } else if (line.startsWith("@@")) {
      lineEl.className += " info";
    }
    
    lineEl.textContent = line;
    content.appendChild(lineEl);
  });
  
  container.appendChild(header);
  container.appendChild(content);
  codingChatLog.appendChild(container);
  scrollChatToBottom();
}

function renderTestResult(event) {
  const box = document.createElement("div");
  box.className = "test-report-box";
  
  const isPassed = event.exit_code === 0;
  const statusClass = isPassed ? "passed" : "failed";
  const icon = isPassed ? "✅ PASSED" : "❌ FAILED";
  
  const header = document.createElement("div");
  header.className = `test-header-row ${statusClass}`;
  header.innerHTML = `<span>🧪 Báo cáo kiểm thử tự động (pytest)</span> <span>${icon}</span>`;
  
  box.appendChild(header);
  
  if (event.stdout || event.stderr) {
    const stdout = (event.stdout || "") + (event.stderr || "");
    const details = document.createElement("div");
    details.className = "test-stdout-details";
    details.textContent = stdout;
    box.appendChild(details);
  }
  
  codingChatLog.appendChild(box);
  scrollChatToBottom();
}

function scrollChatToBottom() {
  codingChatLog.scrollTop = codingChatLog.scrollHeight;
}

// Adjust textarea height automatically based on rows
codingChatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    codingChatForm.requestSubmit();
  }
});
