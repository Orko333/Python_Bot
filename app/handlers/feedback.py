import json
import os
from aiogram import types, Router, F, Bot
from aiogram.filters import Command
from app.config import Config
from app.db import add_feedback, get_feedbacks

router = Router()
FEEDBACK_FILE = "feedback.json"

# Зберегти відгук
def save_feedback(feedback: dict):
    feedbacks = []
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE, "r", encoding="utf-8") as f:
            try:
                feedbacks = json.load(f)
            except Exception:
                feedbacks = []
    feedbacks.append(feedback)
    with open(FEEDBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(feedbacks, f, ensure_ascii=False, indent=2)

# Команда для користувача
@router.message(Command("feedback"))
async def feedback_start(message: types.Message, state=None):
    await message.answer("Залиште, будь ласка, свій відгук про виконане замовлення. Ви можете написати текст і/або оцінку від 1 до 5 зірок (наприклад: 5 ⭐️)")
    # Можна додати FSM для збору оцінки і тексту

@router.message(F.reply_to_message, F.reply_to_message.text.contains("Залиште, будь ласка, свій відгук"))
async def feedback_reply(message: types.Message):
    # Відгук через reply на запит
    feedback = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "text": message.text,
        "stars": int(''.join([c for c in message.text if c.isdigit()]) or 0),
    }
    add_feedback(feedback)
    await message.answer("Дякуємо за ваш відгук!")

@router.message(Command("feedbacks"))
async def feedbacks_admin(message: types.Message):
    if message.from_user.id not in Config.ADMIN_IDS:
        await message.answer("⛔ Тільки адміністратор може переглядати відгуки.")
        return
    feedbacks = get_feedbacks()
    if not feedbacks:
        await message.answer("Відгуків ще немає.")
        return
    text = "<b>Всі відгуки:</b>\n"
    for i, fb in enumerate(feedbacks, 1):
        text += f"\n<b>{i}.</b> @{fb[2]} — {fb[4]}⭐️\n{fb[3]}\n"
    await message.answer(text, parse_mode="HTML")

# Автоматичний запит на відгук (функція для виклику з іншого модуля)
def request_feedback(user_id: int, bot: Bot):
    return bot.send_message(user_id, "Залиште, будь ласка, свій відгук про виконане замовлення. Ви можете написати текст і/або оцінку від 1 до 5 зірок (наприклад: 5 ⭐️)") 