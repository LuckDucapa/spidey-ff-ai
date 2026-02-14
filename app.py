from flask import Flask, request, jsonify, render_template_string
import requests
import os
from datetime import datetime
import sys

app = Flask(__name__)

# --- Configuration ---
# Disable key sorting to keep JSON order
app.json.sort_keys = False

# API Keys
SAMBA_API_KEY = "ca693644-895b-4688-8628-561b3ef6ab9f"
SAMBA_URL = "https://api.sambanova.ai/v1/chat/completions"

# In-memory history storage
request_history = []

# ==========================================
# PUBLIC HOMEPAGE (Beautiful & Animated)
# ==========================================

HOME_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI API Service</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=JetBrains+Mono:wght@400;700&display=swap');
        :root { --bg-color: #09090b; --card-bg: #18181b; --primary: #00ffa3; --secondary: #3b82f6; --text-main: #f4f4f5; --text-muted: #a1a1aa; --border: #27272a; }
        * { box-sizing: border-box; }
        body { background-color: var(--bg-color); color: var(--text-main); font-family: 'Inter', sans-serif; margin: 0; display: flex; justify-content: center; min-height: 100vh; overflow-x: hidden; background-image: radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(0, 255, 163, 0.15) 0px, transparent 50%); }
        .container { width: 100%; max-width: 800px; padding: 40px 20px; animation: fadeIn 1s cubic-bezier(0.22, 1, 0.36, 1); }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }
        header { text-align: center; margin-bottom: 50px; }
        h1 { font-size: 3rem; font-weight: 700; margin: 0; background: linear-gradient(135deg, #fff 0%, #a1a1aa 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: -1px; }
        .status-badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(0, 255, 163, 0.1); color: var(--primary); padding: 6px 12px; border-radius: 20px; font-size: 0.85rem; font-weight: 600; margin-top: 15px; border: 1px solid rgba(0, 255, 163, 0.2); animation: float 3s ease-in-out infinite; }
        .dot { width: 8px; height: 8px; background-color: var(--primary); border-radius: 50%; box-shadow: 0 0 10px var(--primary); }
        .card { background: var(--card-bg); border: 1px solid var(--border); border-radius: 16px; padding: 30px; position: relative; overflow: hidden; transition: all 0.3s ease; }
        .card:hover { border-color: var(--primary); transform: translateY(-2px); box-shadow: 0 10px 40px -10px rgba(0, 0, 0, 0.5); }
        .method { font-family: 'JetBrains Mono', monospace; color: var(--secondary); font-weight: bold; font-size: 1.1rem; margin-bottom: 15px; display: block; }
        .description { color: var(--text-muted); line-height: 1.6; margin-bottom: 25px; }
        .code-block { background: #000; padding: 20px; border-radius: 10px; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; color: #d4d4d8; border: 1px solid #333; position: relative; overflow-x: auto; }
        .param { color: #f472b6; } .value { color: #a78bfa; } .url { color: #60a5fa; }
        footer { text-align: center; margin-top: 50px; color: #555; font-size: 0.9rem; }
        footer span { color: var(--primary); }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>AI API Gateway</h1>
            <div class="status-badge"><span class="dot"></span> Systems Operational</div>
        </header>
        <div class="card">
            <span class="method">GET /ask</span>
            <div class="description">Ask the AI any question. Use limit to ensure the AI gives a short, complete answer.</div>
            <div class="code-block">
                <span class="url">http://spidey-ff-ai.vercel.app/ask</span>?<span class="param">query</span>=<span class="value">Hello</span>&<span class="param">limit</span>=<span class="value">200</span>
            </div>
            <br>
            <div style="font-size: 0.9rem; color: #888;">
                <strong>Parameters:</strong><br>
                • <code>query</code>: Your question (Required)<br>
                • <code>limit</code>: Max characters (Optional)
            </div>
        </div>
        <footer>Built by <span>@spidyabd</span></footer>
    </div>
</body>
</html>
"""

# ==========================================
# PRIVATE HISTORY DASHBOARD (HTML)
# ==========================================

HISTORY_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Secret History Log</title>
    <style>
        body { background: #111; color: #eee; font-family: monospace; padding: 20px; }
        h2 { color: #ff0055; border-bottom: 1px solid #333; padding-bottom: 10px; }
        .stat { margin-bottom: 20px; font-size: 1.2rem; }
        .log { background: #1a1a1a; padding: 15px; margin-bottom: 10px; border-left: 3px solid #00ff88; }
        .time { color: #666; font-size: 0.8rem; }
        .q { color: #fff; font-weight: bold; margin: 5px 0; }
        .a { color: #aaa; font-size: 0.9rem; }
    </style>
</head>
<body>
    <h2>ADMIN ACCESS: History Logs</h2>
    <div class="stat">Total Hits: {{ total_hits }}</div>
    {% for log in logs reversed %}
    <div class="log">
        <div class="time">{{ log.timestamp }}</div>
        <div class="q">Q: {{ log.query }}</div>
        <div class="a">A: {{ log.answer }}</div>
    </div>
    {% endfor %}
</body>
</html>
"""

# ==========================================
# ROUTES
# ==========================================

@app.route("/", methods=["GET"])
def home():
    """Renders the public documentation."""
    return render_template_string(HOME_HTML)

@app.route("/ask", methods=["GET"])
def ask_sambanova():
    if not SAMBA_API_KEY:
        return jsonify({"error": "Configuration Error: API Key missing"}), 500

    query = request.args.get("query")
    limit_param = request.args.get("limit")

    if not query:
        return jsonify({"error": "Missing 'query' parameter"}), 400
        
    headers = {
        "Authorization": f"Bearer {SAMBA_API_KEY}",
        "Content-Type": "application/json",
    }

    # --- PROMPT ENGINEERING LOGIC ---
    # We instruct the AI to be concise via the 'system' message.
    # We do NOT use Python to slice the string afterwards, ensuring a complete thought.
    
    system_instruction = "You are a helpful assistant."

    if limit_param:
        try:
            limit_val = int(limit_param)
            # This prompt ensures the AI finishes its sentence within the count.
            system_instruction = (
                f"You are a helpful assistant. "
                f"Your response must be strictly under {limit_val} characters. "
                f"Provide a summary that is complete and does not cut off mid-sentence."
            )
        except ValueError:
            # If user provides invalid number, fallback to default
            system_instruction = "You are a helpful assistant. Be direct."

    messages = [
        {"role": "system", "content": system_instruction},
        {"role": "user", "content": query}
    ]

    payload = {
        "model": "ALLaM-7B-Instruct-preview",
        "messages": messages,
        "temperature": 0.1,
        "top_p": 0.1
    }

    try:
        response = requests.post(SAMBA_URL, headers=headers, json=payload, timeout=30)
        
        if response.status_code != 200:
            return jsonify({"error": "Model API Error"}), response.status_code

        data = response.json()

        if "choices" in data and len(data["choices"]) > 0:
            answer = data["choices"][0]["message"]["content"]
        else:
            answer = "No response."

        # Save to history (Private)
        request_history.append({
            "query": query,
            "answer": answer,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

        return jsonify({
                "query": query,
                "answer": answer,
                "credit": "@spidyabd"
            })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/history", methods=["GET"])
def get_history():
    key = request.args.get("key")
    response_type = request.args.get("type", "JSON").upper()

    if key != "AIxHISTORY":
        return jsonify({"error": "Invalid API Endpoint", "code": 404}), 404

    total_hits = len(request_history)

    if response_type == "HTML":
        return render_template_string(HISTORY_HTML, logs=request_history, total_hits=total_hits)

    elif response_type == "JSON":
        return jsonify({
            "status": "success",
            "total_hits": total_hits,
            "logs": request_history,
            "credit": "@spidyabd"
        })

    return jsonify({"error": "Invalid Type"}), 400

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"Starting AI-API on port {port} ...")
    app.run(host='0.0.0.0', port=port, debug=True)