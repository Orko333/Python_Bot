import json
import os
from aiogram import types, Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
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

class FeedbackStates(StatesGroup):
    waiting_for_feedback = State()

# Команда для користувача
@router.message(Command("feedback"))
async def feedback_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        await message.delete()
        data = await state.get_data()
        last_info_id = data.get('last_info_message_id')
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        prompt_message = await message.answer("Залиште, будь ласка, свій відгук про виконане замовлення. Ви можете написати текст і/або оцінку від 1 до 5 зірок (наприклад: 5 ⭐️)")
        await state.update_data(last_info_message_id=prompt_message.message_id)
        print(f"[INFO] /feedback: user {user_id} - feedback request sent")
    except Exception as e:
        print(f"[ERROR] /feedback: user {user_id} - {e}")
        sent = await message.answer("Сталася помилка при запиті на відгук.")
        await state.update_data(last_info_message_id=sent.message_id)

@router.message(FeedbackStates.waiting_for_feedback)
async def process_feedback(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_info_id = data.get('last_info_message_id')
    if last_info_id:
        try:
            await message.bot.delete_message(message.chat.id, last_info_id)
        except: pass
    try:
        await message.delete()
    except: pass
        
    feedback = {
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "text": message.text,
        "stars": int(''.join([c for c in message.text if c.isdigit()]) or 0),
    }
    add_feedback(feedback)
    sent = await message.answer("Дякуємо за ваш відгук!")
    await state.update_data(last_info_message_id=sent.message_id)
    await state.clear()

@router.message(Command("feedbacks"))
async def feedbacks_admin(message: types.Message):
    user_id = message.from_user.id
    try:
        if user_id not in Config.ADMIN_IDS:
            await message.answer("⛔️ Тільки адміністратор може переглядати відгуки.")
            print(f"[ERROR] /feedbacks: user {user_id} - not admin")
            return
        feedbacks = get_feedbacks()
        if not feedbacks:
            await message.answer("Відгуків ще немає.")
            print(f"[INFO] /feedbacks: user {user_id} - no feedbacks")
            return
        text = "<b>Всі відгуки:</b>\n"
        for i, fb in enumerate(feedbacks, 1):
            text += f"\n<b>{i}.</b> @{fb[2]} — {fb[4]}⭐️\n{fb[3]}\n"
        await message.answer(text, parse_mode="HTML")
        print(f"[INFO] /feedbacks: user {user_id} - feedbacks sent")
    except Exception as e:
        print(f"[ERROR] /feedbacks: user {user_id} - {e}")
        await message.answer("Сталася помилка при отриманні відгуків.")

# Автоматичний запит на відгук (функція для виклику з іншого модуля)
def request_feedback(user_id: int, bot: Bot):
    return bot.send_message(user_id, "Залиште, будь ласка, свій відгук про виконане замовлення. Ви можете написати текст і/або оцінку від 1 до 5 зірок (наприклад: 5 ⭐️)") 