import logging
import requests
import json
from telegram.ext import Updater, MessageHandler, Filters
from telegram.error import TelegramError
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Загружаем конфигурацию
TG_TOKEN = os.getenv("TG_TOKEN")
FLASK_API_URL = os.getenv("FLASK_API_URL", "http://localhost:5000/telegram")
API_TOKEN = os.getenv("FLASK_API_TOKEN")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "180"))  # 3 минуты по умолчанию

# Проверяем обязательные переменные
if not TG_TOKEN:
    raise ValueError("Не установлен TG_TOKEN в .env файле")
if not API_TOKEN:
    raise ValueError("Не установлен FLASK_API_TOKEN в .env файле")

# Настраиваем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'bot_{datetime.now().strftime("%Y%m%d")}.log')
    ]
)
logger = logging.getLogger(__name__)


def split_long_message(text, max_length=4000):
    """Разделяет длинное сообщение на части"""
    return [text[i:i + max_length] for i in range(0, len(text), max_length)]


def handle_message(update, context):
    """Обработчик входящих сообщений от пользователей"""
    try:
        user_input = update.message.text.strip()
        chat_id = update.message.chat.id
        user_name = update.message.from_user.username or update.message.from_user.first_name
        user_id = update.message.from_user.id

        logger.info(f"Получено сообщение от @{user_name} (ID: {user_id}): {user_input[:200]}...")

        # Показываем пользователю, что бот думает
        context.bot.send_chat_action(chat_id=chat_id, action='typing')

        try:
            # Отправляем запрос в наш Flask API
            response = requests.post(
                FLASK_API_URL,
                json={'prompt': user_input},
                headers={
                    'X-API-TOKEN': API_TOKEN,
                    'Content-Type': 'application/json',
                    'X-User-ID': str(user_id),
                    'X-Username': str(user_name)
                },
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()
            result = response.json()

            if result.get('success'):
                reply = result['response']
                logger.info(f"Успешный ответ для @{user_name} (ID: {user_id}): {len(reply)} символов")
                
                # Разделяем длинные сообщения на части
                for part in split_long_message(reply):
                    context.bot.send_message(
                        chat_id=chat_id,
                        text=part,
                        parse_mode='Markdown',
                        disable_web_page_preview=True
                    )
                return
                
            else:
                error_msg = result.get('error', 'Неизвестная ошибка')
                logger.error(f"Ошибка API для @{user_name} (ID: {user_id}): {error_msg}")
                reply = f"🤖 Ошибка: {error_msg}"

        except requests.exceptions.Timeout:
            logger.error(f"Таймаут запроса от @{user_name} (ID: {user_id})")
            reply = "⏳ Время ожидания ответа истекло. Попробуйте повторить запрос позже."
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка соединения с API для @{user_name} (ID: {user_id}): {str(e)}")
            reply = "❌ Ошибка соединения с сервером. Пожалуйста, попробуйте позже."
            
        except json.JSONDecodeError:
            logger.error(f"Неверный формат ответа от API для @{user_name} (ID: {user_id})")
            reply = "❌ Ошибка обработки ответа сервера."
            
        except Exception as e:
            logger.exception(f"Неожиданная ошибка при обработке запроса от @{user_name} (ID: {user_id})")
            reply = "❌ Произошла внутренняя ошибка. Пожалуйста, попробуйте позже."

        # Отправляем сообщение об ошибке
        context.bot.send_message(
            chat_id=chat_id,
            text=reply,
            parse_mode='Markdown'
        )
        
    except TelegramError as e:
        logger.error(f"Ошибка Telegram при обработке сообщения: {str(e)}")
    except Exception as e:
        logger.exception("Критическая ошибка в обработчике сообщений")


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