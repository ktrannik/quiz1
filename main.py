import json
import random
import sqlite3
import os
import time
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ===== НАСТРОЙКИ =====
TOKEN = "8637399765:AAEM-WJizcYZ2kYIrQoNKJovAXZdTgNYNMU"
ADMIN_ID = 5206039766
QUIZ_FILE = "quizzes.json"

# ===== АНТИСПАМ =====
antispam = {}

def check_antispam(user_id):
    now = time.time()
    user = antispam.get(user_id, {"blocked_until": 0, "last_command": 0, "count": 0})
    
    if user["blocked_until"] > now:
        wait = int(user["blocked_until"] - now)
        return False, f"🚫 *Стоп!* Ты в спам-бане `{wait}` сек.\n📖 Найди викторину в канале."
    
    if now - user["last_command"] < 2.0:
        user["count"] += 1
        user["last_command"] = now
        antispam[user_id] = user
        
        if user["count"] >= 2:
            user["blocked_until"] = now + 20
            user["count"] = 0
            antispam[user_id] = user
            return False, "🚫 *Спам-детект!* Ты слишком часто жмёшь команды.\n⏳ Блокировка `20` сек.\n📖 Полистай канал с викторинами."
        else:
            return False, ""
    
    user["count"] = 0
    user["last_command"] = now
    antispam[user_id] = user
    return True, ""

user_quiz_timers = {}

# ===== БАЗА ДАННЫХ =====
def init_db():
    conn = sqlite3.connect('quiz_users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  total INTEGER DEFAULT 0,
                  rank TEXT DEFAULT "Новичок")''')
    c.execute('''CREATE TABLE IF NOT EXISTS completions
                 (user_id INTEGER,
                  quiz_id TEXT,
                  completed_at TIMESTAMP,
                  PRIMARY KEY (user_id, quiz_id))''')
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def has_completed(user_id, quiz_id):
    conn = sqlite3.connect('quiz_users.db')
    c = conn.cursor()
    c.execute("SELECT 1 FROM completions WHERE user_id = ? AND quiz_id = ?", (user_id, quiz_id))
    result = c.fetchone()
    conn.close()
    return result is not None

def add_completion(user_id, username, quiz_id):
    conn = sqlite3.connect('quiz_users.db')
    c = conn.cursor()
    
    c.execute("INSERT OR IGNORE INTO completions (user_id, quiz_id, completed_at) VALUES (?, ?, ?)",
              (user_id, quiz_id, datetime.now()))
    
    c.execute("SELECT total FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    
    if user:
        new_total = user[0] + 1
        rank = get_rank_by_score(new_total)
        c.execute("UPDATE users SET username = ?, total = ?, rank = ? WHERE user_id = ?",
                  (username, new_total, rank, user_id))
    else:
        rank = get_rank_by_score(1)
        c.execute("INSERT INTO users (user_id, username, total, rank) VALUES (?, ?, ?, ?)",
                  (user_id, username, 1, rank))
    
    conn.commit()
    conn.close()
    return get_user_stats(user_id)

def get_user_stats(user_id):
    conn = sqlite3.connect('quiz_users.db')
    c = conn.cursor()
    c.execute("SELECT total, rank FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    if result:
        return {"total": result[0], "rank": result[1]}
    return {"total": 0, "rank": "Новичок"}

def get_rank_by_score(total):
    if total >= 100:
        return "Гендиректор Организации"
    elif total >= 45:
        return "Первый"
    elif total >= 20:
        return "Багрянник"
    elif total >= 10:
        return "Мироходец"
    else:
        return "Новичок"

# ===== ЗАГРУЗКА ВИКТОРИН =====
def load_quizzes():
    if not os.path.exists(QUIZ_FILE):
        print(f"⚠️ Файл {QUIZ_FILE} не найден, создаю тестовые данные")
        return [
            {"link": "https://t.me/trassa993/1389", "date": "2026-04-15"},
            {"link": "https://t.me/trassa993/1390", "date": "2026-04-15"},
            {"link": "https://t.me/trassa993/1391", "date": "2026-04-16"}
        ]
    try:
        with open(QUIZ_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                print(f"✅ Загружено викторин: {len(data)}")
                return data
            else:
                print(f"⚠️ Файл {QUIZ_FILE} пуст, создаю тестовые данные")
                return [
                    {"link": "https://t.me/trassa993/1389", "date": "2026-04-15"},
                    {"link": "https://t.me/trassa993/1390", "date": "2026-04-15"},
                    {"link": "https://t.me/trassa993/1391", "date": "2026-04-16"}
                ]
    except Exception as e:
        print(f"❌ Ошибка загрузки {QUIZ_FILE}: {e}")
        return [
            {"link": "https://t.me/trassa993/1389", "date": "2026-04-15"},
            {"link": "https://t.me/trassa993/1390", "date": "2026-04-15"},
            {"link": "https://t.me/trassa993/1391", "date": "2026-04-16"}
        ]

# ===== ДЕКОРАТОР АНТИСПАМА =====
def antispam_decorator(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        allowed, msg = check_antispam(user_id)
        if not allowed:
            if msg:
                await update.message.reply_text(msg, parse_mode="Markdown")
            return
        return await func(update, context)
    return wrapper

# ===== КОМАНДЫ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 *Тестовый бот викторин*\n\n"
        "/quiz — случайная викторина\n"
        "/stats — моя статистика\n"
        "/top — топ игроков\n"
        "/donate — поддержать разработку\n"
        "/help — помощь",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Помощь по командам:*\n\n"
        "/quiz — случайная викторина\n"
        "/stats — моя статистика\n"
        "/top — топ игроков\n"
        "/donate — поддержать разработку\n"
        "/help — это сообщение\n\n"
        "🎯 *Как получить +1 к рейтингу:*\n"
        "1. Напиши /quiz\n"
        "2. Перейди по ссылке на викторину\n"
        "3. Подожди 15 секунд\n"
        "4. Нажми «✅ Я прошёл викторину»\n\n"
        "⚠️ *Антиспам:* не чаще 1 команды в 2 секунды, иначе блокировка.",
        parse_mode="Markdown"
    )

@antispam_decorator
async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 Поддержать разработку", url="https://finance.ozon.ru/apps/sbp/ozonbankpay/019da166-0117-7486-83c4-ba6b6a587f43")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💸 *Поддержать разработку бота*\n\n"
        "Если тебе нравятся викторины — можешь отправить донат.\n\n"
        "Спасибо за поддержку! ❤️",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

@antispam_decorator
async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quizzes = load_quizzes()
    if not quizzes:
        await update.message.reply_text("❌ Викторин пока нет")
        return

    q = random.choice(quizzes)
    quiz_id = q["link"].split("/")[-1]
    user_id = update.effective_user.id

    user_quiz_timers[user_id] = {
        "quiz_id": quiz_id,
        "link": q["link"],
        "date": q["date"],
        "start_time": time.time()
    }

    keyboard = [[InlineKeyboardButton("⏳ Станет доступно через 5 сек", callback_data="dummy")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"🎯 *Викторина от {q['date']}*\n\n"
        f"👉 [Пройти викторину]({q['link']})\n\n"
        f"✅ *Перейди по ссылке, посмотри вопрос* (это займёт 5 секунд).\n"
        f"Через 5 секунд кнопка станет активной — нажми её, чтобы получить +1 в рейтинг.\n\n"
        f"*Каждая викторина засчитывается только один раз.*",
        parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=reply_markup
    )

    asyncio.create_task(enable_button_after_delay(context, user_id, update.message.chat_id))

async def enable_button_after_delay(context, user_id, chat_id):
    await asyncio.sleep(5)
    data = user_quiz_timers.get(user_id)
    if data:
        keyboard = [[InlineKeyboardButton("✅ Я прошёл викторину", callback_data="quiz_completed")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"🎯 *Викторина от {data['date']}*\n\n"
                 f"👉 [Пройти викторину]({data['link']})\n\n"
                 f"✅ Кнопка активирована! Нажми, чтобы получить +1 к рейтингу.",
            parse_mode="Markdown",
            disable_web_page_preview=True,
            reply_markup=reply_markup
        )

async def quiz_completed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.first_name

    data = user_quiz_timers.get(user_id)
    if not data:
        await query.edit_message_text("❌ Ошибка: начни викторину заново (/quiz)")
        return

    elapsed = time.time() - data["start_time"]
    if elapsed < 5:
        await query.edit_message_text(
            f"⏳ Подожди ещё {5 - int(elapsed)} секунд.\n"
            f"Это нужно, чтобы убедиться, что ты действительно перешёл по ссылке."
        )
        return

    if has_completed(user_id, data["quiz_id"]):
        await query.edit_message_text("⚠️ Ты уже проходил эту викторину. Попробуй другую через /quiz")
        return

    stats = add_completion(user_id, username, data["quiz_id"])
    await query.edit_message_text(
        f"✅ *Спасибо за прохождение, {query.from_user.first_name}!*\n\n"
        f"📊 Всего викторин пройдено: {stats['total']}\n"
        f"🎖️ Твой ранг: {stats['rank']}\n\n"
        f"👉 [Вернуться к викторине]({data['link']})\n\n"
        f"Попробуй следующую через /quiz",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    del user_quiz_timers[user_id]

@antispam_decorator
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    stats_data = get_user_stats(user.id)
    
    # Пытаемся получить аватарку
    photo = None
    try:
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            photo = photos.photos[0][-1].file_id
    except:
        pass  # Нет аватарки или ошибка доступа
    
    text = (
        f"📊 *Статистика {user.first_name}*:\n\n"
        f"🎯 Викторин пройдено: {stats_data['total']}\n"
        f"🎖️ Ранг: *{stats_data['rank']}*"
    )
    
    if photo:
        await update.message.reply_photo(
            photo=photo,
            caption=text,
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(text, parse_mode="Markdown")

@antispam_decorator
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('quiz_users.db')
    c = conn.cursor()
    c.execute("SELECT username, total, rank FROM users ORDER BY total DESC LIMIT 10")
    top_users = c.fetchall()
    conn.close()
    
    if not top_users:
        await update.message.reply_text("❌ Пока никого нет в рейтинге")
        return
    
    message = "🏆 *Топ-10 игроков:*\n\n"
    for i, (name, total, rank) in enumerate(top_users, 1):
        message += f"{i}. *{name}* — {total} викторин ({rank})\n"
    
    await update.message.reply_text(message, parse_mode="Markdown")

# ===== ЗАГРУЗКА МЕМОВ =====
def load_memes():
    if not os.path.exists('memes.json'):
        print("⚠️ Файл memes.json не найден")
        return []
    with open('memes.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        return []

# ===== КОМАНДА МЕМОВ =====
@antispam_decorator
async def mm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memes = load_memes()
    if not memes:
        await update.message.reply_text("❌ Мемов пока нет")
        return
    
    m = random.choice(memes)
    
    # Если в memes.json есть поле img_url — отправляем картинкой
    if 'img_url' in m and m['img_url']:
        await update.message.reply_photo(
            photo=m['img_url'],
            caption=f"😂 *Мем от {m['date']}*",
            parse_mode="Markdown"
        )
    else:
        # Если только ссылка
        await update.message.reply_text(
            f"😂 *Мем от {m['date']}*\n\n👉 [Смотреть мем]({m['link']})",
            parse_mode="Markdown",
            disable_web_page_preview=True
        )

# ===== ЗАПУСК =====
if __name__ == "__main__":
    init_db()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("donate", donate))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CallbackQueryHandler(quiz_completed, pattern="quiz_completed"))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("mm", mm))  # или другое название команды
    
    print("✅ Тестовый бот запущен!")
    app.run_polling()
