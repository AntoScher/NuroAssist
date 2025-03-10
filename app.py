from flask import Flask, request, jsonify, render_template
import ollama
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Конфигурация модели
MODEL_NAME = "deepseek-r1-distill-qwen-32b"
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
            options={'temperature': 0.7, 'num_ctx': 4096}
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


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)