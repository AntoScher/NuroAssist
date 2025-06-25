import os
from flask import Flask, request, jsonify
import requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

TG_TOKEN   = os.getenv("TG_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_URL")
MODEL_NAME = os.getenv("MODEL_NAME")

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    if not data.get("message") or not data["message"].get("text"):
        return jsonify(ok=True)

    chat_id = data["message"]["chat"]["id"]
    text    = data["message"]["text"]

    # запрос к Ollama
    payload = {"model": MODEL_NAME, "prompt": text, "stream": False}
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
        resp.raise_for_status()
        answer = resp.json().get("response", "").strip()
    except Exception as e:
        answer = f"Ошибка интеграции с Ollama: {e}"

    # отправка ответа в Telegram
    send_url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    requests.post(send_url, json={"chat_id": chat_id, "text": answer})
    return jsonify(ok=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)