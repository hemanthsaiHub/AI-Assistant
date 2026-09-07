// ---------- Panel switching ----------
document.querySelectorAll(".rail-item").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".rail-item").forEach(b => b.classList.remove("is-active"));
    document.querySelectorAll(".panel").forEach(p => p.classList.remove("is-active"));
    btn.classList.add("is-active");
    document.getElementById("panel-" + btn.dataset.panel).classList.add("is-active");
  });
});

async function postJSON(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Request failed");
  return data;
}

// ---------- Chat ----------
const chatLog = document.getElementById("chat-log");
const chatForm = document.getElementById("chat-form");
const chatInput = document.getElementById("chat-input");

function appendMsg(log, role, text) {
  const div = document.createElement("div");
  div.className = "msg msg-" + role;
  div.textContent = text;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

chatForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = chatInput.value.trim();
  if (!message) return;
  appendMsg(chatLog, "user", message);
  chatInput.value = "";
  try {
    const data = await postJSON("/api/chat", { message });
    appendMsg(chatLog, "assistant", data.reply);
  } catch (err) {
    appendMsg(chatLog, "assistant", "Error: " + err.message);
  }
});

document.getElementById("chat-reset").addEventListener("click", async () => {
  await postJSON("/api/reset");
  chatLog.innerHTML = "";
  appendMsg(chatLog, "assistant", "Conversation cleared.");
});

// ---------- Documents ----------
const docStatus = document.getElementById("doc-status");
const docLog = document.getElementById("doc-log");

document.getElementById("doc-upload-btn").addEventListener("click", async () => {
  const fileInput = document.getElementById("doc-file");
  if (!fileInput.files.length) {
    docStatus.textContent = "Choose a file first.";
    return;
  }
  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  docStatus.textContent = "Uploading...";
  try {
    const res = await fetch("/api/upload", { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error);
    docStatus.textContent = `Loaded "${data.filename}" (${data.chunks} sections). Ask a question below.`;
  } catch (err) {
    docStatus.textContent = "Error: " + err.message;
  }
});

document.getElementById("doc-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const input = document.getElementById("doc-question");
  const question = input.value.trim();
  if (!question) return;
  appendMsg(docLog, "user", question);
  input.value = "";
  try {
    const data = await postJSON("/api/askdoc", { question });
    appendMsg(docLog, "assistant", data.answer);
  } catch (err) {
    appendMsg(docLog, "assistant", "Error: " + err.message);
  }
});

// ---------- Recommend ----------
document.getElementById("recommend-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const category = document.getElementById("rec-category").value.trim();
  const preferences = document.getElementById("rec-preferences").value.trim();
  const resultBox = document.getElementById("rec-result");
  if (!category || !preferences) {
    resultBox.textContent = "Fill in both fields.";
    return;
  }
  resultBox.textContent = "Thinking...";
  try {
    const data = await postJSON("/api/recommend", { category, preferences });
    resultBox.textContent = data.result;
  } catch (err) {
    resultBox.textContent = "Error: " + err.message;
  }
});

// ---------- Email ----------
document.getElementById("email-summary-btn").addEventListener("click", async () => {
  const box = document.getElementById("email-summary-result");
  box.textContent = "Checking inbox...";
  try {
    const data = await postJSON("/api/email/summary");
    box.textContent = data.summary;
  } catch (err) {
    box.textContent = "Error: " + err.message;
  }
});

document.getElementById("email-draft-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const instructions = document.getElementById("email-instructions").value.trim();
  const box = document.getElementById("email-draft-result");
  if (!instructions) return;
  box.textContent = "Drafting...";
  try {
    const data = await postJSON("/api/email/draft", { instructions });
    box.textContent = data.result;
  } catch (err) {
    box.textContent = "Error: " + err.message;
  }
});
