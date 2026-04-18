import json
import random
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = "8637399765:AAEM-WJizcYZ2kYIrQoNKJovAXZdTgNYNMU"
ADMIN_ID = 5206039766
QUIZ_FILE = "quizzes.json"

def load_quizzes():
    if not os.path.exists(QUIZ_FILE):
        return []
    with open(QUIZ_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_quizzes(quizzes):
    with open(QUIZ_FILE, "w", encoding="utf-8") as f:
        json.dump(quizzes, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 *Бот викторин*\n\n"
        "/quiz — случайная викторина\n"
        "/stats — сколько викторин в базе\n"
        "/add ссылка1 ссылка2 ссылка3 — добавить несколько викторин",
        parse_mode="Markdown"
    )

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quizzes = load_quizzes()
    if not quizzes:
        await update.message.reply_text("❌ Викторин пока нет")
        return
    q = random.choice(quizzes)
    await update.message.reply_text(
        f"🎯 *{q['date']}*\n\n👉 [Пройти викторину]({q['link']})",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    quizzes = load_quizzes()
    await update.message.reply_text(f"📊 Викторин в базе: {len(quizzes)}")

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Нет прав")
        return
    
    if not context.args:
        await update.message.reply_text("📎 /add ссылка1 ссылка2 ссылка3")
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

app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("quiz", quiz))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("add", add))

print("✅ Бот запущен!")
app.run_polling()
