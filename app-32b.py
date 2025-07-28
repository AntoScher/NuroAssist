from flask import Flask, request, jsonify, render_template
import ollama
from dotenv import load_dotenv
import logging
import os
import secrets

load_dotenv()

app = Flask(__name__)

# Генерируем или загружаем секретный токен для защиты API
# ЗАМЕНИТЕ ЭТУ ЧАСТЬ
# API_TOKEN = "ваш_секретный_токен"

# НА ЭТУ:
# Генерируем или загружаем секретный токен для защиты API
API_TOKEN = os.getenv("FLASK_API_TOKEN")
if not API_TOKEN:
    API_TOKEN = secrets.token_urlsafe(32)
    with open('.env', 'a') as f:
        f.write(f"\nFLASK_API_TOKEN={API_TOKEN}\n")
    print(f"\n===== СГЕНЕРИРОВАН НОВЫЙ API ТОКЕН =====")
    print(f"FLASK_API_TOKEN={API_TOKEN}")
    print(f"=======================================\n")
# Конфигурация модели DeepSeek-R1-Distill-Qwen-32B
MODEL_NAME = "deepseek-r1:32b"
SYSTEM_PROMPT = "Ты - профессиональный ассистент. Отвечай точно и структурированно."


def process_query(prompt):
    """Общая функция обработки запросов к модели"""
    try:
        response = ollama.generate(
            model=MODEL_NAME,
            prompt=f"{SYSTEM_PROMPT}\n\n{prompt}",
            stream=False,
            options={
                'temperature': 0.7,
                'num_ctx': 4096,
                'num_gpu': 50,
                'num_thread': 8
            }
        )
        return {
            'success': True,
            'response': response['response']
        }
    except Exception as e:
        app.logger.error(f"Ошибка при генерации ответа: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@app.route('/')
def index():
    """Веб-интерфейс"""
    return render_template('index.html')


@app.route('/ask', methods=['POST'])
def ask_assistant():
    """Эндпоинт для веб-интерфейса"""
    data = request.json
    prompt = data.get('prompt', '')

    if not prompt:
        return jsonify({'success': False, 'error': 'Пустой запрос'}), 400

    return jsonify(process_query(prompt))


@app.route('/telegram', methods=['POST'])
def telegram_handler():
    """Эндпоинт для Telegram бота (защищен токеном)"""
    # Проверка токена для безопасности
    token = request.headers.get('X-API-TOKEN')
    if token != API_TOKEN:
        app.logger.warning("Попытка неавторизованного доступа к /telegram")
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    data = request.json
    prompt = data.get('prompt', '')

    if not prompt:
        return jsonify({'success': False, 'error': 'Пустой запрос'}), 400

    return jsonify(process_query(prompt))


# Настраиваем логирование
app.logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
app.logger.addHandler(handler)

if __name__ == '__main__':
    app.logger.info(f"Запуск Flask API на порту 5000. API_TOKEN: {API_TOKEN[:8]}...")
    app.run(host='0.0.0.0', port=5000, debug=False)