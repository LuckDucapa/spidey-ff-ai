import os
import requests
import re
import random
from flask import Flask, request, jsonify, redirect

app = Flask(__name__)
app.json.sort_keys = False 

# --- CONFIGURATION ---
# OpenRouter Key from Vercel Environment Variables
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

# Reliable Free Chat Model
CHAT_MODEL = "xiaomi/mimo-v2-flash:free" 
CREDIT_TAG = "@spidey_abd"

def get_chat_headers():
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://vercel.app", 
        "X-Title": "Vercel API"
    }

# ==========================================
#  1. CHAT ENDPOINT (Unchanged)
# ==========================================
@app.route('/chat', methods=['GET'])
def chat():
    user_query = request.args.get('query')
    limit_arg = request.args.get('limit')
    
    if not user_query:
        return jsonify({"query": "None", "answer": "Error: No query provided", "credit": CREDIT_TAG}), 400

    if limit_arg and limit_arg.isdigit():
        char_limit = int(limit_arg)
        max_tokens_calc = int(char_limit / 3) + 50
        system_prompt = (
            f"You are a helpful assistant. "
            f"1. Answer strictly in less than {char_limit} characters. "
            "2. Be concise. "
            "3. Do NOT use Markdown (no * or #). Plain text only."
        )
    else:
        system_prompt = (
            "You are a helpful assistant. "
            "1. Provide a detailed, comprehensive answer. "
            "2. Do NOT use Markdown formatting. "
            "3. Write in plain text paragraphs. "
        )
        max_tokens_calc = 2000 

    payload = {
        "model": CHAT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens_calc
    }

    try:
        response = requests.post(OPENROUTER_CHAT_URL, headers=get_chat_headers(), json=payload)
        
        if response.status_code != 200:
            err_msg = f"API Error {response.status_code}"
            try:
                err_msg += f": {response.json().get('error', {}).get('message', '')}"
            except:
                err_msg += f": {response.text}"
            return jsonify({"query": user_query, "answer": err_msg, "credit": CREDIT_TAG}), 500

        data = response.json()
        
        if "choices" in data and len(data["choices"]) > 0:
            raw_answer = data["choices"][0]["message"]["content"]
            clean_answer = re.sub(r'[\*\#]', '', raw_answer)
            clean_answer = re.sub(r'\n+', '\n', clean_answer).strip()

            return jsonify({
                "query": user_query,
                "answer": clean_answer,
                "credit": CREDIT_TAG
            })
        else:
            return jsonify({"query": user_query, "answer": "Error: Empty response.", "credit": CREDIT_TAG}), 500

    except Exception as e:
        return jsonify({"query": user_query, "answer": str(e), "credit": CREDIT_TAG}), 500


# ==========================================
#  2. IMAGE ENDPOINT (Redirect Fix)
# ==========================================
@app.route('/image', methods=['GET'])
def image():
    prompt = request.args.get('prompt')
    if not prompt: return "Error: No prompt provided", 400

    # 1. Clean the prompt (Remove weird symbols that might break the URL)
    clean_prompt = re.sub(r'[^\w\s\-\.\,]', '', prompt) 
    
    # 2. Add Random Seed (Prevents Pollinations from rejecting duplicate requests)
    seed = random.randint(0, 999999)

    # 3. Build URL
    # We send the user DIRECTLY to Pollinations. 
    # This bypasses the Python blocking and the Vercel timeout.
    pollinations_url = f"https://image.pollinations.ai/prompt/{clean_prompt}?width=1024&height=1024&nologo=true&seed={seed}&model=flux"

    # 4. HTTP 302 Redirect
    return redirect(pollinations_url, code=302)

# For local testing
if __name__ == '__main__':
    app.run()
