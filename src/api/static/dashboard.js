const API_BASE = "/api/v1/tasks";
const POLL_MS = 1500;

// The exact 10 lifecycle stages requested
const STAGES = [
  { id: "request", title: "User Request", icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>` },
  { id: "fastapi", title: "FastAPI", icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"></rect><line x1="8" y1="21" x2="16" y2="21"></line><line x1="12" y1="17" x2="12" y2="21"></line></svg>` },
  { id: "queue", title: "Celery Queue", icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"></path></svg>` },
  { id: "redis", title: "Redis Broker", icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="9" ry="3"></ellipse><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path><path d="M21 19c0 1.66-4 3-9 3s-9-1.34-9-3"></path></svg>` },
  { id: "worker", title: "Celery Worker", icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="4" width="16" height="16" rx="2"></rect><rect x="9" y="9" width="6" height="6"></rect><line x1="9" y1="1" x2="9" y2="4"></line><line x1="15" y1="1" x2="15" y2="4"></line><line x1="9" y1="20" x2="9" y2="23"></line><line x1="15" y1="20" x2="15" y2="23"></line><line x1="20" y1="9" x2="23" y2="9"></line><line x1="20" y1="15" x2="23" y2="15"></line><line x1="1" y1="9" x2="4" y2="9"></line><line x1="1" y1="15" x2="4" y2="15"></line></svg>` },
  { id: "orchestrator", title: "LangGraph Orchestrator", icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>` },
  { id: "researcher", title: "ResearchAgent", icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>` },
  { id: "writer", title: "WritingAgent", icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 20h9"></path><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path></svg>` },
  { id: "approval", title: "Human Approval", icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3"></path></svg>` },
  { id: "result", title: "Final Result", icon: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>` },
];

let currentTaskId = null;
let pollHandle = null;
let clockInterval = null;
let timerInterval = null;
let taskStartTime = null;

// DOM Elements
const createForm = document.getElementById("create-task-form");
const promptInput = document.getElementById("prompt");
const startBtn = document.getElementById("start-btn");
const taskIdInput = document.getElementById("task-id-input");
const trackBtn = document.getElementById("track-task-btn");
const demoBtns = document.querySelectorAll(".demo-prompt-btn");

const taskIdEl = document.getElementById("task-id");
const copyIdBtn = document.getElementById("copy-id-btn");
const taskStatusEl = document.getElementById("task-status");
const taskElapsedEl = document.getElementById("task-elapsed");
const taskCurrentAgentEl = document.getElementById("task-current-agent");

const workflowEl = document.getElementById("workflow-nodes");
const svgCanvas = document.getElementById("pipeline-svg");
const logsEl = document.getElementById("agent-logs");
const logCountEl = document.getElementById("log-count");
const resultEl = document.getElementById("final-result");
const copyResultBtn = document.getElementById("copy-result-btn");
const connectionStateEl = document.getElementById("connection-state");
const systemClockEl = document.getElementById("system-clock");

const approvalPanel = document.getElementById("approval-panel");
const approvalFeedback = document.getElementById("approval-feedback");
const approveBtn = document.getElementById("approve-btn");
const rejectBtn = document.getElementById("reject-btn");
const approvalMessageEl = document.getElementById("approval-message");

// Initialize Clock
startClock();

// Render initial empty node pipeline graph
renderWorkflow(0, "NOT_STARTED");

// Event Listeners
createForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const prompt = promptInput.value.trim();
  if (!prompt) return;

  setConnectionState("SUBMITTING", "badge-running");
  startBtn.disabled = true;

  try {
    const response = await fetch(API_BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });

    if (!response.ok) throw new Error(await response.text());

    const data = await response.json();
    currentTaskId = data.task_id;
    taskStartTime = Date.now();
    taskIdInput.value = currentTaskId;
    approvalFeedback.value = "";
    approvalMessageEl.textContent = "";

    setConnectionState("RUNNING", "badge-running");
    startPolling();
    startTimer();
  } catch (err) {
    setConnectionState("ERROR", "badge-danger");
    showApprovalMessage(`Task Creation Failed: ${err.message}`, true);
  } finally {
    startBtn.disabled = false;
  }
});

trackBtn.addEventListener("click", () => {
  const val = taskIdInput.value.trim();
  if (!val) return;

  currentTaskId = val;
  taskStartTime = Date.now();
  approvalFeedback.value = "";
  approvalMessageEl.textContent = "";
  setConnectionState("POLLING", "badge-running");
  startPolling();
  startTimer();
});

demoBtns.forEach((btn) => {
  btn.addEventListener("click", () => {
    promptInput.value = btn.dataset.prompt;
    promptInput.focus();
  });
});

copyIdBtn.addEventListener("click", () => {
  if (currentTaskId) {
    navigator.clipboard.writeText(currentTaskId);
    copyIdBtn.title = "Copied!";
    setTimeout(() => (copyIdBtn.title = "Copy UUID"), 2000);
  }
});

copyResultBtn.addEventListener("click", () => {
  const text = resultEl.textContent;
  if (text) {
    navigator.clipboard.writeText(text);
  }
});

approveBtn.addEventListener("click", () => submitApproval(true));
rejectBtn.addEventListener("click", () => submitApproval(false));

// Polling & Timer Functions
function startPolling() {
  stopPolling();
  fetchTaskStatus();
  pollHandle = setInterval(fetchTaskStatus, POLL_MS);
}

function stopPolling() {
  if (pollHandle) {
    clearInterval(pollHandle);
    pollHandle = null;
  }
}

function startTimer() {
  if (timerInterval) clearInterval(timerInterval);
  timerInterval = setInterval(updateTimerDisplay, 1000);
  updateTimerDisplay();
}

function stopTimer() {
  if (timerInterval) {
    clearInterval(timerInterval);
    timerInterval = null;
  }
}

function updateTimerDisplay() {
  if (!taskStartTime) return;
  const elapsed = Math.max(0, Date.now() - taskStartTime);
  taskElapsedEl.textContent = formatDuration(elapsed);
}

async function fetchTaskStatus() {
  if (!currentTaskId) return;

  try {
    const res = await fetch(`${API_BASE}/${currentTaskId}`);
    if (!res.ok) throw new Error(await res.text());

    const task = await res.json();
    renderTaskDetails(task);

    if (["COMPLETED", "FAILED"].includes(task.status)) {
      stopPolling();
      stopTimer();
      setConnectionState(
        task.status === "COMPLETED" ? "COMPLETED" : "FAILED",
        task.status === "COMPLETED" ? "badge-success" : "badge-danger"
      );
    }
  } catch (err) {
    setConnectionState("OFFLINE", "badge-danger");
  }
}

async function submitApproval(approved) {
  if (!currentTaskId) return;

  approveBtn.disabled = true;
  rejectBtn.disabled = true;
  showApprovalMessage(approved ? "Submitting approval..." : "Submitting rejection...", false);

  try {
    const res = await fetch(`${API_BASE}/${currentTaskId}/approve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        approved,
        feedback: approvalFeedback.value.trim() || null,
      }),
    });

    if (!res.ok) throw new Error(await res.text());

    const data = await res.json();
    showApprovalMessage(`Decision registered! Workflow status: ${data.status}`, false);
    setConnectionState("RESUMED", "badge-running");
    startPolling();
  } catch (err) {
    showApprovalMessage(`Approval Failed: ${err.message}`, true);
  } finally {
    approveBtn.disabled = false;
    rejectBtn.disabled = false;
  }
}

// Rendering Logic
function renderTaskDetails(task) {
  taskIdEl.textContent = task.id;
  copyIdBtn.classList.remove("hidden");

  taskStatusEl.textContent = task.status;
  taskStatusEl.className = `badge ${getStatusBadgeClass(task.status)}`;

  // Calculate stage index
  const stageIndex = calculateStageIndex(task);
  const activeStage = STAGES[stageIndex] ? STAGES[stageIndex].title : "--";
  taskCurrentAgentEl.textContent = activeStage;

  // Render nodes
  renderWorkflow(stageIndex, task.status);

  // Render logs
  renderLogs(task.agent_logs || []);

  // Render result
  if (task.result) {
    resultEl.textContent = task.result;
    copyResultBtn.disabled = false;
  } else {
    resultEl.textContent = "Processing... Output will appear here upon completion.";
    copyResultBtn.disabled = true;
  }

  // Handle Human Approval Gate visibility
  if (task.status === "AWAITING_APPROVAL") {
    approvalPanel.classList.remove("hidden");
    setConnectionState("AWAITING_APPROVAL", "badge-warning");
  } else {
    approvalPanel.classList.add("hidden");
  }
}

function renderWorkflow(currentIndex, status) {
  workflowEl.innerHTML = "";

  STAGES.forEach((stage, idx) => {
    const card = document.createElement("div");
    card.className = "node-card";

    let stateClass = "state-pending";
    let statusText = "Pending";

    if (status === "FAILED" && idx === currentIndex) {
      stateClass = "state-failed";
      statusText = "Failed";
    } else if (idx < currentIndex || status === "COMPLETED") {
      stateClass = "state-completed";
      statusText = "Done";
    } else if (idx === currentIndex) {
      if (status === "AWAITING_APPROVAL") {
        stateClass = "state-awaiting";
        statusText = "Approval Required";
      } else {
        stateClass = "state-current";
        statusText = "Active";
      }
    }

    card.classList.add(stateClass);

    card.innerHTML = `
      <div class="node-card-header">
        <span class="node-number">0${idx + 1}</span>
        <div class="node-icon-wrapper">${stage.icon}</div>
      </div>
      <div>
        <h3 class="node-title">${stage.title}</h3>
        <div class="node-status-text">${statusText}</div>
      </div>
    `;

    workflowEl.appendChild(card);
  });

  // Draw connecting SVG lines between nodes
  requestAnimationFrame(drawPipelineConnections);
}

function drawPipelineConnections() {
  const cards = workflowEl.querySelectorAll(".node-card");
  if (!cards.length) return;

  const containerRect = workflowEl.getBoundingClientRect();
  svgCanvas.setAttribute("width", containerRect.width);
  svgCanvas.setAttribute("height", containerRect.height);

  let pathsHTML = "";
  for (let i = 0; i < cards.length - 1; i++) {
    const c1 = cards[i].getBoundingClientRect();
    const c2 = cards[i + 1].getBoundingClientRect();

    const x1 = c1.right - containerRect.left;
    const y1 = c1.top + c1.height / 2 - containerRect.top;
    const x2 = c2.left - containerRect.left;
    const y2 = c2.top + c2.height / 2 - containerRect.top;

    const isCompleted = cards[i].classList.contains("state-completed");
    const strokeColor = isCompleted ? "#10b981" : "#1f293d";
    const strokeWidth = isCompleted ? "2" : "1.5";

    pathsHTML += `
      <path d="M ${x1} ${y1} L ${x2} ${y2}" 
            stroke="${strokeColor}" 
            stroke-width="${strokeWidth}" 
            stroke-dasharray="${isCompleted ? "none" : "4 4"}" 
            fill="none" />
    `;
  }

  svgCanvas.innerHTML = svgCanvas.querySelector("defs").outerHTML + pathsHTML;
}

function renderLogs(logs) {
  logCountEl.textContent = `${logs.length} ${logs.length === 1 ? "entry" : "entries"}`;

  if (!logs.length) {
    logsEl.innerHTML = `
      <div class="log-empty-state">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
        <p>No agent logs recorded for this task yet.</p>
      </div>
    `;
    return;
  }

  const html = logs
    .slice()
    .reverse()
    .map((log) => {
      const time = log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : "--:--:--";
      const agent = log.agent || "Agent";
      const action = log.action || "Log entry";
      
      let agentClass = "";
      if (agent.toLowerCase().includes("research")) agentClass = "agent-researcher";
      else if (agent.toLowerCase().includes("writing")) agentClass = "agent-writer";
      else if (agent.toLowerCase().includes("orchestrator")) agentClass = "agent-orchestrator";

      return `
        <div class="log-item ${agentClass}">
          <div class="log-item-head">
            <span class="log-agent-name">${escapeHtml(agent)}</span>
            <span>${escapeHtml(time)}</span>
          </div>
          <div class="log-action-text">${escapeHtml(action)}</div>
        </div>
      `;
    })
    .join("");

  logsEl.innerHTML = html;
}

function calculateStageIndex(task) {
  const status = task.status;

  if (status === "PENDING") return 2; // Celery Queue
  if (status === "RESEARCHING") return 6; // ResearchAgent
  if (status === "WRITING") return 7; // WritingAgent
  if (status === "AWAITING_APPROVAL") return 8; // Human Approval Gate
  if (status === "COMPLETED") return 9; // Final Result
  if (status === "FAILED") return 9;
  if (status === "RESUMED") return 5; // LangGraph Orchestrator

  if (status === "RUNNING" || status === "RETRYING") {
    const logs = task.agent_logs || [];
    const latest = logs[logs.length - 1] || {};
    const agent = (latest.agent || "").toLowerCase();

    if (agent.includes("research")) return 6;
    if (agent.includes("writing")) return 7;
    if (agent.includes("orchestrator")) return 5;
    return 4; // Worker
  }

  return 1; // FastAPI
}

function getStatusBadgeClass(status) {
  switch (status) {
    case "AWAITING_APPROVAL": return "badge-warning";
    case "COMPLETED": return "badge-success";
    case "FAILED": return "badge-danger";
    case "RUNNING":
    case "RESEARCHING":
    case "WRITING":
    case "RESUMED": return "badge-running";
    default: return "badge-neutral";
  }
}

function setConnectionState(text, badgeClass) {
  connectionStateEl.textContent = text;
  connectionStateEl.className = `badge ${badgeClass}`;
}

function showApprovalMessage(msg, isError) {
  approvalMessageEl.textContent = msg;
  approvalMessageEl.style.color = isError ? "var(--danger)" : "var(--text-muted)";
}

function startClock() {
  updateClock();
  clockInterval = setInterval(updateClock, 1000);
}

function updateClock() {
  const now = new Date();
  systemClockEl.textContent = now.toLocaleTimeString();
}

function formatDuration(ms) {
  const totalSec = Math.floor(ms / 1000);
  const hrs = Math.floor(totalSec / 3600);
  const mins = Math.floor((totalSec % 3600) / 60);
  const secs = totalSec % 60;

  const pad = (n) => String(n).padStart(2, "0");
  return `${pad(hrs)}:${pad(mins)}:${pad(secs)}`;
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

window.addEventListener("resize", drawPipelineConnections);

