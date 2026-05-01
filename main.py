import json
import random
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
TOKEN = "8637399765:AAEM-WJizcYZ2kYIrQoNKJovAXZdTgNYNMU"
ADMIN_ID = 5206039766
QUIZ_FILE = "quizzes.json"
MEMES_FILE = "memes.json"

# ===== ЗАГРУЗКА ДАННЫХ =====
def load_quizzes():
    if not os.path.exists(QUIZ_FILE):
        return []
    with open(QUIZ_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        return []

def load_memes():
    if not os.path.exists(MEMES_FILE):
        return []
    with open(MEMES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        return []

def save_quizzes(quizzes):
    with open(QUIZ_FILE, "w", encoding="utf-8") as f:
        json.dump(quizzes, f, ensure_ascii=False, indent=2)

def save_memes(memes):
    with open(MEMES_FILE, "w", encoding="utf-8") as f:
        json.dump(memes, f, ensure_ascii=False, indent=2)

# ===== ОПРЕДЕЛЕНИЕ ТИПА ПОСТА =====
def detect_post_type(text):
    text_lower = text.lower()
    if "#игра_бога" in text_lower or "викторина" in text_lower:
        return "quiz"
    elif "#мемло" in text_lower or "мем" in text_lower:
        return "meme"
    else:
        return "quiz"

# ===== КОМАНДЫ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 *Бот викторин и мемов*\n\n"
        "/quiz — случайная викторина\n"
        "/meme — случайный мем\n"
        "/stats — статистика\n"
        "/donate — поддержать разработку\n"
        "/help — помощь\n\n"
        "📎 *Как добавить викторину/мем:*\n"
        "Просто перешли пост из канала сюда — бот сам определит тип и добавит!",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Помощь по командам:*\n\n"
        "/quiz — получить случайную викторину\n"
        "/meme — получить случайный мем\n"
        "/stats — статистика (сколько викторин и мемов в базе)\n"
        "/donate — поддержать разработку\n\n"
        "❓ *Возникли проблемы?* Напиши @n1kita53",
        parse_mode="Markdown"
    )


async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 Поддержать разработку", url="https://finance.ozon.ru/apps/sbp/ozonbankpay/019da166-0117-7486-83c4-ba6b6a587f43")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💸 *Поддержать разработку бота*\n\n"
        "Если тебе нравятся викторины и ты хочешь помочь с развитием — можешь отправить донат.\n\n"
        "Спасибо за поддержку! ❤️",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quizzes = load_quizzes()
    if not quizzes:
        await update.message.reply_text("❌ Викторин пока нет")
        return
    q = random.choice(quizzes)
    await update.message.reply_text(
        f"🎯 *Викторина от {q['date']}*\n\n👉 [Пройти викторину]({q['link']})",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

async def meme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    memes = load_memes()
    if not memes:
        await update.message.reply_text("❌ Мемов пока нет")
        return
    m = random.choice(memes)
    await update.message.reply_text(
        f"😂 *Мем от {m['date']}*\n\n👉 [Смотреть мем]({m['link']})",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quizzes = load_quizzes()
    memes = load_memes()
    await update.message.reply_text(
        f"📊 *Статистика:*\n\n"
        f"🎯 Викторин: {len(quizzes)}\n"
        f"😂 Мемов: {len(memes)}",
        parse_mode="Markdown"
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет прав")
        return
    
    if not context.args:
        await update.message.reply_text(
            "📎 *Как добавить викторины:*\n"
            "`/add ссылка1 ссылка2 ссылка3`\n\n"
            "Пример:\n"
            "`/add https://t.me/kanal/123 https://t.me/kanal/456`",
            parse_mode="Markdown"
        )
        return
    
    links = context.args
    quizzes = load_quizzes()
    today = datetime.now().strftime("%Y-%m-%d")
    added = 0
    errors = []
    
    for link in links:
        if not link.startswith("https://t.me/"):
            errors.append(f"❌ Неверная ссылка: {link[:50]}...")
            continue
        
        if any(q["link"] == link for q in quizzes):
            errors.append(f"⚠️ Уже есть: {link[:50]}...")
            continue
        
        quizzes.append({
            "link": link,
            "date": today
        })
        added += 1
    
    if added:
        save_quizzes(quizzes)
        await update.message.reply_text(f"✅ Добавлено викторин: {added}")
    
    if errors:
        await update.message.reply_text("\n".join(errors[:5]))

# ===== ОБРАБОТЧИК ПЕРЕСЛАННЫХ ПОСТОВ =====
async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Игнорируем пересылки в группах / каналах
    if update.message.chat.type != "private":
        return
    
    if not update.message.forward_origin:
        await update.message.reply_text("❌ Перешлите пост из канала")
        return
    
    origin = update.message.forward_origin
    channel = None
    
    if hasattr(origin, 'chat') and origin.chat:
        channel = origin.chat
    else:
        await update.message.reply_text("❌ Не могу определить источник пересылки")
        return
    
    channel_username = channel.username if channel.username else None
    
    if not channel_username:
        await update.message.reply_text("❌ У канала нет username, не могу создать ссылку")
        return
    
    try:
        post_id = update.message.forward_origin.message_id
    except:
        await update.message.reply_text("❌ Не могу определить ID поста")
        return
    
    # Пытаемся получить реальную дату поста
    post_date = None
    try:
        if hasattr(update.message, 'forward_date') and update.message.forward_date:
            from datetime import datetime as dt
            post_date = dt.fromtimestamp(update.message.forward_date).strftime("%Y-%m-%d")
    except:
        pass
    
    if not post_date:
        post_date = datetime.now().strftime("%Y-%m-%d")
    
    link = f"https://t.me/{channel_username}/{post_id}"
    text = update.message.caption or ""
    
    post_type = detect_post_type(text)
    
    if post_type == "quiz":
        quizzes = load_quizzes()
        if link not in [q["link"] for q in quizzes]:
            quizzes.append({"link": link, "date": post_date})
            save_quizzes(quizzes)
            await update.message.reply_text(f"✅ Викторина добавлена!\n{link}\n📅 Дата поста: {post_date}")
        else:
            await update.message.reply_text("⚠️ Такая викторина уже есть")
    else:
        memes = load_memes()
        if link not in [m["link"] for m in memes]:
            memes.append({"link": link, "date": post_date})
            save_memes(memes)
            await update.message.reply_text(f"✅ Мем добавлен!\n{link}\n📅 Дата поста: {post_date}")
        else:
            await update.message.reply_text("⚠️ Такой мем уже есть")
# ===== ЗАПУСК =====
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("donate", donate))
app.add_handler(CommandHandler("quiz", quiz))
app.add_handler(CommandHandler("meme", meme))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("add", add))
app.add_handler(MessageHandler(filters.FORWARDED, handle_forward))

print("✅ Бот запущен!")
app.run_polling()
