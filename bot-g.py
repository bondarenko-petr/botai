import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import google.generativeai as genai

# Загрузка токенов
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Настройка Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-1.5-flash")

# Загрузка справочной информации
with open("data/programs.txt", "r", encoding="utf-8") as f:
    admission_info = f.read()

# Функция запроса к Gemini
async def ask_gemini(question: str) -> str:
    prompt_text = f"""Ты помощник приемной комиссии. Используй только эту информацию при ответе:\n\n{admission_info}\n\nВопрос: {question}"""
    response = model.generate_content(prompt_text)
    return response.text.strip()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я ассистент приёмной комиссии. Задай вопрос.")

# Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    await update.message.reply_text("Секунду, думаю...")

    try:
        answer = await ask_gemini(question)
        await update.message.reply_text(answer)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

# Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()