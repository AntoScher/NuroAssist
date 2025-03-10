from flask import Flask, request, jsonify, render_template
import ollama
from dotenv import load_dotenv
import logging
import traceback

load_dotenv()

app = Flask(__name__)

# Конфигурация модели для 14B версии
MODEL_NAME = "deepseek-r1:14b"  # Убедитесь, что модель скачана через ollama pull
SYSTEM_PROMPT = """Ты - русскоязычный ассистент. Отвечай точно и кратко. 
Текущая дата: {current_date}""".format(current_date="10.03.2024")  # Можно динамически обновлять

# Настройка логирования
logging.basicConfig(level=logging.INFO)
app.logger.addHandler(logging.FileHandler('assistant.log'))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/ask', methods=['POST'])
def ask_assistant():
    try:
        data = request.json
        prompt = data.get('prompt', '')

        if not prompt:
            return jsonify({'success': False, 'error': 'Пустой запрос'}), 400

        # Параметры для GTX 1050 Ti (4GB VRAM)
        options = {
            'temperature': 0.7,
            'num_ctx': 2048,  # Уменьшенный контекст
            'num_gpu': 25,  # 25% слоев на GPU (безопасно для 4GB)
            'num_thread': 4,  # 4 ядра из 6 доступных
            'low_vram': True,  # Критически важно!
            'stop': ['\n']  # Остановка после первого ответа
        }

        app.logger.info(f"Запрос: {prompt}")

        response = ollama.generate(
            model=MODEL_NAME,
            prompt=f"{SYSTEM_PROMPT}\n\nВопрос: {prompt}\nОтвет:",
            stream=False,
            options=options
        )

        return jsonify({
            'success': True,
            'response': response['response'].strip()
        })

    except Exception as e:
        app.logger.error(f"Ошибка: {traceback.format_exc()}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)  # Обязательно threaded=True!