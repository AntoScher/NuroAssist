from flask import Flask, request, jsonify, render_template
import ollama
from dotenv import load_dotenv
import logging


load_dotenv()

app = Flask(__name__)

# Конфигурация модели DeepSeek-R1-Distill-Qwen-..........B
MODEL_NAME = "deepseek-r1:14b"
SYSTEM_PROMPT = "Ты - профессиональный ассистент. Отвечай точно и структурированно."


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/ask', methods=['POST'])
def ask_assistant():

    try:
        data = request.json
        prompt = data.get('prompt', '')

        response = ollama.generate(
            model=MODEL_NAME,
            prompt=f"{SYSTEM_PROMPT}\n\n{prompt}",
            stream=False,
            #options={'temperature': 0.7, 'num_ctx': 4096}
        options = {'temperature': 0.7,
                   'num_ctx': 2048,
                   'num_gpu': 45,
                   'num_thread': 6}
        )

        return jsonify({
            'success': True,
            'response': response['response']
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

app.logger.setLevel(logging.INFO)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)