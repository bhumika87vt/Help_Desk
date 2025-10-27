const messages = document.getElementById("messages");
const promptInput = document.getElementById("prompt");
const sendBtn = document.getElementById("send");
const micBtn = document.getElementById("mic");
const speakChk = document.getElementById("speak");

function addMsg(text, who = "user") {
  const div = document.createElement("div");
  div.className = `msg ${who}`;
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
}

async function askServer(question) {
  const res = await fetch("/ask", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ question })
  });
  const data = await res.json();
  return data.answer || "Sorry, I couldn't understand.";
}

async function handleSend() {
  const q = promptInput.value.trim();
  if (!q) return;
  addMsg(q, "user");
  promptInput.value = "";
  const ans = await askServer(q);
  addMsg(ans, "bot");
  if (speakChk.checked && "speechSynthesis" in window) {
    const u = new SpeechSynthesisUtterance(ans);
    u.lang = "en-IN";
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  }
}

sendBtn.addEventListener("click", handleSend);
promptInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") handleSend();
});

// Voice input (Chrome/Edge only)
let recognition = null;
if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  recognition = new SR();
  recognition.lang = "en-IN";
  recognition.interimResults = false;
  recognition.maxAlternatives = 1;

  micBtn.addEventListener("mousedown", () => {
    micBtn.classList.add("rec");
    recognition.start();
  });
  micBtn.addEventListener("mouseup", () => {
    recognition.stop();
  });
  recognition.onresult = (e) => {
    const text = e.results[0][0].transcript;
    promptInput.value = text;
    handleSend();
  };
  recognition.onerror = () => {
    micBtn.classList.remove("rec");
  };
  recognition.onend = () => {
    micBtn.classList.remove("rec");
  };
} else {
  // Browser doesn't support speech input
  micBtn.disabled = true;
  micBtn.title = "Voice input not supported in this browser";
}
