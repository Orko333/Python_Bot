import json
import os
from aiogram import types, Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.config import Config
from app.db import add_support_log, log_message
from app.utils.validation import is_command

router = Router()
SUPPORT_LOG = "support_log.json"

# Логування чату у БД
def log_support(user_id, admin_id, message, direction):
    add_support_log({
        "user_id": user_id,
        "admin_id": admin_id,
        "message": message,
        "direction": direction
    })

class SupportStates(StatesGroup):
    waiting_for_message = State()
    in_dialog = State()

# Користувач ініціює підтримку
@router.message(Command("support"))
async def support_start(message: types.Message, state: FSMContext):
    await state.update_data(last_user_message_id=message.message_id)
    user_id = message.from_user.id
    try:
        sent = await message.answer("Напишіть своє питання або уточнення. Менеджер отримає ваше повідомлення і відповість тут у чаті.")
        await state.update_data(last_bot_message_id=sent.message_id)
        log_message(message.from_user.id, message.from_user.username, 'user', message.text, message.chat.id)
        print(f"[INFO] /support: user {user_id} - support started")
    except Exception as e:
        print(f"[ERROR] /support: user {user_id} - {e}")
        sent = await message.answer("Сталася помилка при зверненні до підтримки.")
        await state.update_data(last_bot_message_id=sent.message_id)

# Пересилка повідомлення користувача адміну
@router.message(SupportStates.waiting_for_message)
async def support_user_message(message: types.Message, state: FSMContext, bot: Bot):
    await state.update_data(last_user_message_id=message.message_id)
    if is_command(message.text):
        return False
    try:
        sent = await message.answer("Ваше питання надіслано менеджеру. Очікуйте відповідь тут у чаті. Наступні повідомлення також будуть пересилатись.")
        await state.update_data(last_bot_message_id=sent.message_id)
        await state.set_state(SupportStates.in_dialog)
        log_message(message.from_user.id, message.from_user.username, 'user', message.text, message.chat.id)
    except Exception as e:
        sent = await message.answer("Сталася помилка при надсиланні питання.")
        await state.update_data(last_bot_message_id=sent.message_id)

@router.message(SupportStates.in_dialog, ~F.text.startswith('/'))
async def support_dialog_message(message: types.Message, bot: Bot):
    for admin_id in Config.ADMIN_IDS:
        await bot.send_message(
            admin_id,
            f"<b>Повідомлення від <code>{message.from_user.id}</code></b>\n\n{message.text}",
            parse_mode="HTML"
        )
    await message.answer("Повідомлення надіслано.", reply_markup=types.ReplyKeyboardRemove())
    log_message(message.from_user.id, message.from_user.username, 'user', message.text, message.chat.id)

# Адмін відповідає користувачу через reply
@router.message(F.reply_to_message, F.from_user.id.in_(Config.ADMIN_IDS))
async def support_admin_reply(message: types.Message, bot: Bot):
    reply = message.reply_to_message
    if not reply.text:
        return

    user_id_str = None
    if "Питання від користувача" in reply.text:
        user_id_str = reply.text.split("<code>")[1].split("</code>")[0]
    elif "Повідомлення від" in reply.text:
        user_id_str = reply.text.split("<code>")[1].split("</code>")[0]

    if user_id_str:
        try:
            user_id = int(user_id_str)
            await bot.send_message(user_id, f"<b>Відповідь менеджера:</b>\n{message.text}", parse_mode="HTML")
            await message.answer("✅ Відповідь надіслано.")
        except (ValueError, IndexError):
            await message.answer("⚠️ Не вдалося визначити користувача для відповіді.")
    else:
        await message.answer("⚠️ Не вдалося визначити користувача. Відповідайте на правильне повідомлення.")
    log_message(message.from_user.id, message.from_user.username, 'user', message.text, message.chat.id) 