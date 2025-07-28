import logging
import requests
from telegram.ext import Updater, MessageHandler, Filters
import os
from dotenv import load_dotenv

load_dotenv()

# Загружаем конфигурацию
TG_TOKEN = os.getenv("TG_TOKEN")
FLASK_API_URL = os.getenv("FLASK_API_URL", "http://localhost:5000/telegram")
API_TOKEN = os.getenv("FLASK_API_TOKEN")

# Проверяем обязательные переменные
if not TG_TOKEN:
    raise ValueError("Не установлен TG_TOKEN в .env файле")
if not API_TOKEN:
    raise ValueError("Не установлен FLASK_API_TOKEN в .env файле")

# Настраиваем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def handle_message(update, context):
    """Обработчик входящих сообщений от пользователей"""
    user_input = update.message.text
    chat_id = update.message.chat.id
    user_name = update.message.from_user.username or update.message.from_user.first_name

    logger.info(f"Получено сообщение от @{user_name} (ID: {chat_id}): {user_input}")

    # Показываем пользователю, что бот думает
    context.bot.send_chat_action(chat_id=chat_id, action='typing')

    try:
        # Отправляем запрос в наш Flask API
        response = requests.post(
            FLASK_API_URL,
            json={'prompt': user_input},
            headers={'X-API-TOKEN': API_TOKEN},
            timeout=180  # Увеличенный таймаут для обработки больших моделей
        )

        response.raise_for_status()
        result = response.json()

        if result.get('success'):
            reply = result['response']
            logger.info(f"Ответ для @{user_name}: {reply[:100]}...")
        else:
            error_msg = result.get('error', 'Неизвестная ошибка')
            logger.error(f"Ошибка обработки запроса: {error_msg}")
            reply = f"🤖 Ошибка при обработке запроса: {error_msg}"

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка соединения с API: {str(e)}")
        reply = "❌ Не удалось соединиться с сервером. Попробуйте позже."
    except Exception as e:
        logger.exception("Неожиданная ошибка при обработке запроса")
        reply = "❌ Произошла внутренняя ошибка. Попробуйте позже."

    # Отправляем ответ пользователю
    context.bot.send_message(
        chat_id=chat_id,
        text=reply,
        parse_mode='Markdown'
    )


def error_handler(update, context):
    """Обработчик ошибок"""
    logger.error(f"Произошла ошибка: {context.error}")
    if update and update.effective_message:
        context.bot.send_message(
            chat_id=update.effective_message.chat_id,
            text="❌ Произошла ошибка при обработке вашего запроса."
        )


def main():
    """Основная функция запуска бота"""
    updater = Updater(TG_TOKEN, use_context=True)
    dp = updater.dispatcher

    # Добавляем обработчики
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_error_handler(error_handler)

    logger.info(f"Telegram бот запущен. Ожидание сообщений...")
    logger.info(f"Подключение к Flask API: {FLASK_API_URL}")

    # Запускаем бота
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()