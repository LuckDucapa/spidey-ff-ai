import os
import requests
import re
import urllib.parse
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# --- CONFIGURATION ---
app.json.sort_keys = False 

# NOTE: On Vercel, you must add 'OPENROUTER_API_KEY' in the Vercel Project Settings > Environment Variables
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") # Don't hardcode keys for Vercel deployment
OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

CHAT_MODEL = "xiaomi/mimo-v2-flash:free" 
CREDIT_TAG = "@spidey_abd"

def get_chat_headers():
    return {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://vercel.com", 
        "X-Title": "Vercel API"
    }

# ==========================================
#  1. CHAT ENDPOINT
# ==========================================
@app.route('/chat', methods=['GET'])
def chat():
    user_query = request.args.get('query')
    limit_arg = request.args.get('limit')
    
    if not user_query:
        return jsonify({
            "query": "None", 
            "answer": "Error: No query provided", 
            "credit": CREDIT_TAG
        }), 400

    if limit_arg and limit_arg.isdigit():
        char_limit = int(limit_arg)
        max_tokens_calc = int(char_limit / 3) + 50
        system_prompt = (
            f"You are a helpful assistant. "
            f"1. Answer strictly in less than {char_limit} characters. "
            "2. Be concise. "
            "3. Do NOT use Markdown formatting (no asterisks *, no hashes #). Plain text only."
        )
    else:
        system_prompt = (
            "You are a helpful assistant. "
            "1. Provide a detailed, comprehensive answer. "
            "2. Do NOT use Markdown formatting (no asterisks *, no hashes #). "
            "3. Write in plain text paragraphs. "
            "4. Be fast but thorough."
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
#  2. IMAGE ENDPOINT
# ==========================================
@app.route('/image', methods=['GET'])
def image():
    prompt = request.args.get('prompt')
    if not prompt: return "Error: No prompt provided", 400

    encoded_prompt = urllib.parse.quote(prompt)
    pollinations_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

    try:
        # Note: Vercel Free tier has a 10s timeout. Pollinations is usually fast enough.
        img_response = requests.get(pollinations_url, stream=True, timeout=9) 
        
        if img_response.status_code == 200:
            return Response(img_response.content, mimetype='image/jpeg')
        else:
            return f"Error from Pollinations AI: {img_response.status_code}", 502

    except Exception as e:
        return f"Server Error: {str(e)}", 500

# Vercel handles the execution, so app.run() is not needed here, 
# but we leave it for local testing if you run 'python api/index.py'
if __name__ == '__main__':
    app.run()