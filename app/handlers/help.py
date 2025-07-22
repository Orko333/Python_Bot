from aiogram import types, Router
from aiogram.filters import Command
from app.config import Config
from aiogram.fsm.context import FSMContext
from app.utils.validation import delete_previous_messages, delete_all_tracked_messages, is_command
from app.db import log_message

router = Router()

@router.message(Command("help"))
async def help_handler(message: types.Message, state: FSMContext):
    await delete_all_tracked_messages(message.bot, message.chat.id, state)
    await state.update_data(last_user_message_id=message.message_id)
    user_id = message.from_user.id
    try:
        try:
            await message.delete()
        except Exception as del_exc:
            print(f"[WARNING] /help: не вдалося видалити повідомлення: {del_exc}")
        text = (
            "<b>Доступні команди:</b>\n"
            "/start — Головне меню\n"
            "/order — Зробити нове замовлення\n"
            "/cabinet — Мої замовлення\n"
            "/faq — Часті питання\n"
            "/prices — Прайс-лист\n"
            "/feedback — Залишити відгук\n"
            "/support — Зв'язок з менеджером\n"
            "/help — Список команд\n"
        )
        if user_id in Config.ADMIN_IDS:
            text += (
                "\n<b>Для адміністраторів:</b>\n"
                "/orders — Всі замовлення\n"
                "/order_[номер] — Переглянути деталі замовлення (наприклад: /order_5)\n"
                "/setstatus_[номер]_[статус] — Змінити статус замовлення (наприклад: /setstatus_5_done)\n"
                "/stats — Статистика\n"
                "/addpromo_[код]_[тип]_[значення]_[ліміт] — Додати промокод (наприклад: /addpromo_SUMMER2024_percent_10_100)\n"
                "/promos — Статистика промокодів\n"
                "/feedbacks — Всі відгуки\n"
            )
        await delete_all_tracked_messages(message.bot, message.chat.id, state)
        sent = await message.answer(text, parse_mode="HTML")
        await state.update_data(last_bot_message_id=sent.message_id)
        print(f"[INFO] /help: user {user_id} - help sent")
    except Exception as e:
        print(f"[ERROR] /help: user {user_id} - {e}")
        await delete_all_tracked_messages(message.bot, message.chat.id, state)
        sent = await message.answer("Сталася помилка при отриманні списку команд.")
        await state.update_data(last_bot_message_id=sent.message_id) 