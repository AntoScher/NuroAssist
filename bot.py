import logging
import requests
from telegram.ext import Updater, MessageHandler, Filters
import os

from dotenv import load_dotenv

load_dotenv()


TELEGRAM_TOKEN   = os.getenv("TG_TOKEN")
OLLAMA_URL = os.getenv("OLLAMA_URL")
MODEL_NAME = os.getenv("MODEL_NAME")


#TELEGRAM_TOKEN = 'вставь_токен_бота_сюда'
#OLLAMA_URL = 'http://localhost:11434/api/generate'
#MODEL_NAME = 'deepseek-r1:32b'

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def handle_message(update, context):
    user_input = update.message.text
    chat_id = update.message.chat.id

    # Отправляем запрос в Ollama
    try:
        response = requests.post(
            OLLAMA_URL,
            json={'model': MODEL_NAME, 'prompt': user_input, 'stream': False},
            timeout=60
        )
        response.raise_for_status()
        reply = response.json().get('response', '🤖 Модель не ответила.')
    except Exception as e:
        logger.error(f"Ошибка запроса к Ollama: {e}")
        reply = f"❌ Ошибка: {e}"

    context.bot.send_message(chat_id=chat_id, text=reply)

def main():
    updater = Updater(TELEGRAM_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    logger.info("Бот запущен. Ожидаю сообщений…")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()