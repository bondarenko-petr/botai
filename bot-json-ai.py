import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-flash")

with open("data/programs.json", "r", encoding="utf-8") as f:
    admission_info = f.read()

async def ask_gemini(question: str) -> str:
    prompt_text = f"""
Ты помощник приёмной комиссии Волгоградского государственного университета.
Используй только эту информацию для ответа:
{admission_info}

Вопрос: {question}

Если в этих данных нет точного ответа, сделай поиск через Google 
только по направлениям подготовки в университетах и возможным профессиям выпускников.
Не выдумывай, не уходи в посторонние темы.

Ответ:
"""
    response = model.generate_content(prompt_text)
    return response.text.strip()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я помощник приёмной комиссии. Задай вопрос.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    await update.message.reply_text("Секунду, думаю...")

    try:
        answer = await ask_gemini(question)
        await update.message.reply_text(answer)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
