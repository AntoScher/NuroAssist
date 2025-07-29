from flask import Flask, request, jsonify, render_template
import requests
from dotenv import load_dotenv
import logging
import os
import secrets
import json
from functools import wraps
from datetime import datetime, timedelta
from collections import defaultdict

load_dotenv()

app = Flask(__name__)

# Конфигурация
API_TOKEN = os.getenv("FLASK_API_TOKEN")
if not API_TOKEN:
    API_TOKEN = secrets.token_urlsafe(32)
    with open('.env', 'a') as f:
        f.write(f"\nFLASK_API_TOKEN={API_TOKEN}\n")
    print("\n===== СГЕНЕРИРОВАН НОВЫЙ API ТОКЕН =====")
    print(f"FLASK_API_TOKEN={API_TOKEN[:8]}...")
    print("=======================================\n")

# Ollama настройки
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-r1:32b")
SYSTEM_PROMPT = os.getenv("SYSTEM_PROMPT", "Ты - профессиональный ассистент. Отвечай точно и структурированно.")
MAX_PROMPT_LENGTH = int(os.getenv("MAX_PROMPT_LENGTH", "4000"))
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "60"))  # запросов в минуту

# Логирование URL (не показываем полный URL в логах)
app.logger.info(f"Используется Ollama URL: {OLLAMA_URL.split('@')[-1] if '@' in OLLAMA_URL else OLLAMA_URL}")

# Конфигурация модели
MODEL_CONFIG = {
    'temperature': float(os.getenv('MODEL_TEMPERATURE', '0.7')),
    'num_ctx': int(os.getenv('MODEL_NUM_CTX', '4096')),
    'num_gpu': int(os.getenv('MODEL_NUM_GPU', '50')),
    'num_thread': int(os.getenv('MODEL_NUM_THREAD', '8'))
}

# Для ограничения запросов
request_logs = defaultdict(list)

def rate_limited(max_per_minute):
    """Декоратор для ограничения количества запросов"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            ip = request.remote_addr
            now = datetime.now()
            
            # Удаляем старые записи
            request_logs[ip] = [t for t in request_logs[ip] if now - t < timedelta(minutes=1)]
            
            if len(request_logs[ip]) >= max_per_minute:
                app.logger.warning(f"Превышен лимит запросов для IP: {ip}")
                return jsonify({
                    'success': False,
                    'error': 'Слишком много запросов. Пожалуйста, подождите.'
                }), 429
                
            request_logs[ip].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def process_query(prompt):
    """Общая функция обработки запросов к модели"""
    try:
        # Валидация длины промпта
        if len(prompt) > MAX_PROMPT_LENGTH:
            return {
                'success': False,
                'error': f'Слишком длинный запрос. Максимальная длина: {MAX_PROMPT_LENGTH} символов'
            }

        # Подготавливаем данные для запроса
        request_data = {
            'model': MODEL_NAME,
            'prompt': f"{SYSTEM_PROMPT}\n\n{prompt}",
            'stream': False,
            'options': MODEL_CONFIG
        }
        
        # Отправляем запрос к Ollama API
        response = requests.post(
            OLLAMA_URL,
            json=request_data,
            timeout=300  # 2 минуты таймаут
        )
        
        # Проверяем статус ответа
        response.raise_for_status()
        result = response.json()
        
        # Проверяем наличие поля 'response' в ответе
        if 'response' not in result:
            app.logger.error(f"Неожиданный формат ответа от Ollama: {result}")
            return {
                'success': False,
                'error': 'Неверный формат ответа от модели'
            }
        
        return {
            'success': True,
            'response': result['response']
        }
        
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Ошибка при запросе к Ollama API: {str(e)}", exc_info=True)
        if hasattr(e, 'response') and e.response is not None:
            try:
                error_details = e.response.json().get('error', 'Нет дополнительной информации')
                app.logger.error(f"Детали ошибки от Ollama: {error_details}")
                return {
                    'success': False,
                    'error': f'Ошибка модели: {error_details}'
                }
            except:
                pass
                
        return {
            'success': False,
            'error': 'Ошибка при обращении к API модели. Проверьте, запущен ли сервер Ollama.'
        }
        
    except json.JSONDecodeError as e:
        app.logger.error(f"Ошибка декодирования JSON от Ollama: {str(e)}")
        return {
            'success': False,
            'error': 'Ошибка при обработке ответа от модели'
        }
        
    except Exception as e:
        app.logger.error(f"Неожиданная ошибка: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }


@app.route('/')
def index():
    """Веб-интерфейс"""
    return render_template('index.html')


@app.route('/ask', methods=['POST'])
@rate_limited(RATE_LIMIT)
def ask_assistant():
    """Эндпоинт для веб-интерфейса"""
    if not request.is_json:
        return jsonify({'success': False, 'error': 'Неверный формат запроса'}), 400
        
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({'success': False, 'error': 'Отсутствует обязательное поле prompt'}), 400
        
    prompt = data.get('prompt', '').strip()
    if not prompt:
        return jsonify({'success': False, 'error': 'Пустой запрос'}), 400

    return jsonify(process_query(prompt))


@app.route('/telegram', methods=['POST'])
@rate_limited(RATE_LIMIT)
def telegram_handler():
    """Эндпоинт для Telegram бота (защищен токеном)"""
    # Проверка токена для безопасности
    token = request.headers.get('X-API-TOKEN')
    if not token or token != API_TOKEN:
        app.logger.warning("Попытка неавторизованного доступа к /telegram")
        return jsonify({'success': False, 'error': 'Unauthorized'}), 401

    if not request.is_json:
        return jsonify({'success': False, 'error': 'Неверный формат запроса'}), 400
        
    data = request.get_json()
    if not data or 'prompt' not in data:
        return jsonify({'success': False, 'error': 'Отсутствует обязательное поле prompt'}), 400
        
    prompt = data.get('prompt', '').strip()
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

@app.route('/health')
def health_check():
    """Проверка работоспособности сервиса"""
    return jsonify({
        'status': 'ok',
        'service': 'NuroAssist API',
        'model': MODEL_NAME,
        'version': '1.0.0',
        'timestamp': datetime.utcnow().isoformat()
    })


if __name__ == '__main__':
    app.logger.info("Запуск Flask API на порту 5000")
    app.run(host='0.0.0.0', port=5000, debug=False)