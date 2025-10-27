import json
import socket
import urllib.request
from io import BytesIO
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
import qrcode
from difflib import SequenceMatcher
import threading
import subprocess
import time

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "knowledge_base.json"

app = Flask(__name__, static_folder="static", template_folder="templates")

# ---------------- NETWORK HANDLING ----------------

def get_local_ip():
    """Return the local LAN IP."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def get_ngrok_url():
    """Retrieve the public ngrok URL if available."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels") as response:
            data = json.load(response)
            for tunnel in data.get("tunnels", []):
                if "public_url" in tunnel:
                    return tunnel["public_url"]
    except Exception:
        return None

def start_ngrok():
    """Start ngrok tunnel automatically."""
    try:
        subprocess.Popen(["ngrok", "http", "5000"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("⚠️  Ngrok not found. Install from https://ngrok.com/download and connect your account.")
        print("   Once installed, run: ngrok config add-authtoken <YOUR_TOKEN>")

# ---------------- KNOWLEDGE BASE ----------------

def load_kb():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

KB = load_kb()

# ---------------- TEXT & QUERY SYSTEM ----------------

def normalize_text(q):
    """Simplify synonyms."""
    synonyms = {
        "faculties": "faculty",
        "professors": "faculty",
        "teachers": "faculty",
        "lecturers": "faculty",
        "staffs": "staff",
        "incharge": "hod",
        "head of department": "hod",
        "leader": "hod",
        "head": "hod",
        "dept": "department",
        "block": "department"
    }
    q = q.lower().strip()
    for word, replacement in synonyms.items():
        q = q.replace(word, replacement)
    return q

def similarity(a, b):
    """Calculate similarity ratio."""
    return SequenceMatcher(None, a, b).ratio()

def find_department(query_lc):
    """Find department info."""
    for dept in KB.get("departments", []):
        name = dept.get("name", "").lower()
        short = dept.get("short", "").lower()
        if name in query_lc or short in query_lc:
            return dept
    return None

def answer_query(query):
    """Smart query answering."""
    q = normalize_text(query)

    def intent_match(words):
        return any(k in q or similarity(q, k) > 0.65 for k in words)

    if intent_match(["principal", "head of college"]):
        p = KB.get("college", {}).get("principal", {})
        return f"Principal: {p.get('name', 'Not available')}"

    if intent_match(["fees", "exam fee", "payment"]):
        fees = KB.get("fees", {})
        return f"Tuition Last Date: {fees.get('tuition_fee_last_date', 'N/A')}, Exam Fee Last Date: {fees.get('exam_fee_last_date', 'N/A')}."

    if intent_match(["hod", "head of department"]):
        dept = find_department(q)
        if dept:
            return f"HOD of {dept['name']}: {dept.get('hod', 'Not available')}"
        return "Please mention a department, e.g., 'CSE HOD'."

    if intent_match(["faculty", "professor", "staff"]):
        dept = find_department(q)
        if dept:
            members = ", ".join(f['name'] for f in dept.get("faculty", []))
            return f"{dept['name']} Faculty Members: {members}"
        return "Please specify the department, e.g., 'CSE faculty'."

    return "I can help with details about HOD, faculty, fees, or departments."

# ---------------- ROUTES ----------------

@app.route("/")
def home():
    base_url = getattr(app, "public_url", None)
    if not base_url:
        base_url = f"http://{get_local_ip()}:5000"
    college_name = KB.get("college", {}).get("name", "Our College")
    return render_template("index.html", base_url=base_url, college_name=college_name)

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json(force=True)
    query = (data.get("question") or "").strip()
    if not query:
        return jsonify({"answer": "Please type a question."})
    answer = answer_query(query)
    return jsonify({"answer": answer})

@app.route("/qr")
def qr():
    url = getattr(app, "public_url", None)
    if not url:
        url = f"http://{get_local_ip()}:5000"
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

# ---------------- RUN SERVER ----------------

if __name__ == "__main__":
    print("🚀 Starting Flask server...")

    # Start ngrok tunnel for global access
    threading.Thread(target=start_ngrok).start()
    print("🌐 Creating public ngrok tunnel... Please wait 5–10 seconds.")

    # Wait for tunnel availability
    time.sleep(8)
    app.public_url = get_ngrok_url()

    if app.public_url:
        print(f"✅ PUBLIC URL: {app.public_url}")
        print("📱 Scan the QR code generated at /qr to open it from any Wi-Fi or mobile network.")
    else:
        print("⚠️ Could not detect ngrok link. The app is only accessible on local Wi-Fi.")

    app.run(host="0.0.0.0", port=5000, debug=True)
