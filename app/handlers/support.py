import json
import os
from aiogram import types, Router, F, Bot
from aiogram.filters import Command
from app.config import Config
from app.db import add_support_log

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

# Користувач ініціює підтримку
@router.message(Command("support"))
async def support_start(message: types.Message, state=None):
    await message.answer(
        "Напишіть своє питання або уточнення. Менеджер отримає ваше повідомлення і відповість тут у чаті."
    )
    # Ставимо state, якщо треба FSM

# Пересилка повідомлення користувача адміну
@router.message(F.reply_to_message == None, ~Command("support"))
async def support_user_message(message: types.Message, bot: Bot):
    if message.text and message.text.startswith("/"):
        return  # Не пересилаємо команди
    # Пересилаємо всім адміністраторам
    for admin_id in Config.ADMIN_IDS:
        fwd = await bot.send_message(
            admin_id,
            f"<b>Питання від користувача</b> <code>{message.from_user.id}</code>\n"
            f"Ім'я: {message.from_user.full_name}\n"
            f"Username: @{message.from_user.username}\n"
            f"\n{message.text}",
            parse_mode="HTML",
            reply_markup=types.ForceReply(selective=True)
        )
        log_support(message.from_user.id, admin_id, message.text, "user2admin")
    await message.answer("Ваше питання надіслано менеджеру. Очікуйте відповідь тут у чаті.")

# Адмін відповідає користувачу через reply
@router.message(F.reply_to_message)
async def support_admin_reply(message: types.Message, bot: Bot):
    # Витягуємо user_id з тексту reply_to_message
    reply = message.reply_to_message
    lines = reply.text.splitlines()
    user_id = None
    for line in lines:
        if line.startswith("Питання від користувача"):
            try:
                user_id = int(line.split()[3])
            except Exception:
                pass
    if not user_id:
        await message.answer("Не вдалося визначити користувача для відповіді.")
        return
    # Надсилаємо відповідь користувачу
    await bot.send_message(user_id, f"<b>Відповідь менеджера:</b>\n{message.text}", parse_mode="HTML")
    log_support(user_id, message.from_user.id, message.text, "admin2user")
    await message.answer("Відповідь надіслано користувачу.") 