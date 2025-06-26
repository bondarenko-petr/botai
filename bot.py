import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
from openai import OpenAI

# Загружаем токены из .env
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Создаём клиента OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Загружаем текст с информацией для поступающих
with open("data/programs.txt", "r", encoding="utf-8") as f:
    admission_info = f.read()

# Запрос к OpenAI
async def ask_openai(question: str) -> str:
    messages = [
        {"role": "system", "content": "Ты помощник приёмной комиссии. Отвечай только на основе информации ниже."},
        {"role": "user", "content": f"{admission_info}\n\nВопрос: {question}"}
    ]
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.2,
        max_tokens=700,
    )
    return response.choices[0].message.content.strip()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я ассистент для поступающих. Задай свой вопрос.")

# Обработка сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    question = update.message.text
    await update.message.reply_text("Секунду, ищу ответ...")

    try:
        answer = await ask_openai(question)
        await update.message.reply_text(answer)
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка: {e}")

# Запуск приложения
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

if __name__ == "__main__":
    app.run_polling()