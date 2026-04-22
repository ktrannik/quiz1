import json
import random
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8637399765:AAEM-WJizcYZ2kYIrQoNKJovAXZdTgNYNMU"
ADMIN_ID = 5206039766
QUIZ_FILE = "quizzes.json"
MEMES_FILE = "memes.json"
# История последних выданных викторин (чтобы не повторять подряд)
last_quizzes = []

# ===== ЗАГРУЗКА ДАННЫХ =====
def load_quizzes():
    if not os.path.exists(QUIZ_FILE):
        return []
    with open(QUIZ_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_memes():
    if not os.path.exists(MEMES_FILE):
        return []
    with open(MEMES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_quizzes(quizzes):
    with open(QUIZ_FILE, "w", encoding="utf-8") as f:
        json.dump(quizzes, f, ensure_ascii=False, indent=2)

# ===== КОМАНДЫ =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 *Бот викторин и мемов*\n\n"
        "/quiz — случайная викторина\n"
        "/meme — случайный мем\n"
        "/stats — статистика\n"
        "/donate — поддержать разработку\n"
        "/help — помощь",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Помощь по командам:*\n\n"
        "/quiz — получить случайную викторину\n"
        "/meme — получить случайный мем\n"
        "/stats — показать количество викторин и мемов в базе\n"
        "/donate — поддержать разработку бота\n\n"
        "Бот работает 24/7, первая команда после простоя может быть долгой (15-30 сек)."
        "Если возникла проблема, пиши @n1kita53",
        parse_mode="Markdown"
    )

async def donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💳 СБП", url="https://finance.ozon.ru/apps/sbp/ozonbankpay/019da166-0117-7486-83c4-ba6b6a587f43")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "💸 *Поддержать разработку бота*\n\n"
        "Нажми на кнопку ниже, чтобы перевести по СБП.\n"
        "Спасибо за поддержку! ❤️",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_quizzes
    quizzes = load_quizzes()
    if not quizzes:
        await update.message.reply_text("❌ Викторин пока нет")
        return
    
    # Если в истории больше 10 викторин — убираем старые
    if len(last_quizzes) > 10:
        last_quizzes = last_quizzes[-10:]
    
    # Фильтруем те, что не были в последних 5 выдачах
    available = [q for q in quizzes if q["link"] not in last_quizzes[-5:]]
    
    # Если все викторины были в истории — берём любую
    if not available:
        available = quizzes
    
    q = random.choice(available)
    
    # Добавляем в историю
    last_quizzes.append(q["link"])
    
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
    today = datetime.now().strftime("%d.%m.%Y")
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

# ===== ЗАПУСК =====
app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("donate", donate))
app.add_handler(CommandHandler("quiz", quiz))
app.add_handler(CommandHandler("meme", meme))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("add", add))

print("✅ Бот запущен!")
app.run_polling()