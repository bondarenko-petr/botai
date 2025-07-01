import os
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-flash")

# Загружаем данные об образовательных программах
with open("data/programs.json", "r", encoding="utf-8") as f:
    admission_info = f.read()

# Папка для хранения файлов сессий пользователей
SESSION_STORAGE_DIR = "data/user_histories"
os.makedirs(SESSION_STORAGE_DIR, exist_ok=True)

# В оперативной памяти храним сессии пользователей:
# { user_id: { "messages": [...], "last_active": datetime } }
user_sessions = {}

# Константы
SESSION_TIMEOUT = timedelta(minutes=15)  # Время неактивности для удаления сессии
MAX_MESSAGES = 5  # Максимум сообщений в истории

def session_file_path(user_id: int) -> str:
    return os.path.join(SESSION_STORAGE_DIR, f"user_{user_id}.json")

def save_session_to_file(user_id: int):
    if user_id not in user_sessions:
        return
    data = user_sessions[user_id]["messages"]
    path = session_file_path(user_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"История пользователя {user_id} сохранена в файл {path}")

def load_session_from_file(user_id: int):
    path = session_file_path(user_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Ограничиваем максимум сообщений на всякий случай
        return data[-MAX_MESSAGES:]
    return []

async def ask_gemini(question: str, history: list[str]) -> str:
    # Формируем историю в текст
    history_text = "\n".join(history)
    prompt_text = f"""
Ты помощник приёмной комиссии Волгоградского государственного университета.

Вот история общения с пользователем:
{history_text}

Вот данные об образовательных программах:
{admission_info}

Вопрос: {question}

Используй только эти данные для ответа. 
Если точного ответа в этих данных нет — просто скажи, что информация отсутствует.
Не выдумывай и не переходи к посторонним темам.
"""
    response = model.generate_content(prompt_text)
    return response.text.strip()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # При старте пытаемся загрузить предыдущую сессию из файла
    messages = load_session_from_file(user_id)
    user_sessions[user_id] = {
        "messages": messages,
        "last_active": datetime.utcnow()
    }

    await update.message.reply_text(
        "Привет! Я помощник приёмной комиссии. Задай вопрос."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    question = update.message.text.strip()

    # Если сессия отсутствует в памяти, грузим из файла или создаём новую
    if user_id not in user_sessions:
        messages = load_session_from_file(user_id)
        user_sessions[user_id] = {
            "messages": messages,
            "last_active": datetime.utcnow()
        }

    session = user_sessions[user_id]
    session["last_active"] = datetime.utcnow()

    # Добавляем вопрос пользователя
    session["messages"].append(f"Пользователь: {question}")
    # Оставляем только последние MAX_MESSAGES сообщений (вопрос-ответ считаем как отдельные)
    session["messages"] = session["messages"][-MAX_MESSAGES:]

    await update.message.reply_text("Секунду, думаю...")

    try:
        answer = await ask_gemini(question, session["messages"])
        session["messages"].append(f"Ассистент: {answer}")
        # Опять ограничиваем размер истории
        session["messages"] = session["messages"][-MAX_MESSAGES:]
        await update.message.reply_text(answer)
    except Exception as e:
        await update.message.reply_text(f"Ошибка: {e}")

async def cleanup_sessions_loop():
    while True:
        now = datetime.utcnow()
        to_remove = []

        for user_id, session in user_sessions.items():
            last_active = session["last_active"]
            if now - last_active > SESSION_TIMEOUT:
                # Сохраняем в файл и удаляем из памяти
                save_session_to_file(user_id)
                to_remove.append(user_id)
                print(f"Сессия пользователя {user_id} удалена (неактивен > {SESSION_TIMEOUT})")

        for user_id in to_remove:
            del user_sessions[user_id]

        await asyncio.sleep(60)  # Проверять каждую минуту

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем цикл очистки неактивных сессий
    app.job_queue.run_once(lambda ctx: asyncio.create_task(cleanup_sessions_loop()), when=0)

    print("Бот запущен")
    app.run_polling()
