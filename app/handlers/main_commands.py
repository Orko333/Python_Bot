from aiogram import types, Router, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from .start import ORDER_TYPES # Assuming ORDER_TYPES is in start.py
from magic_filter import F

router = Router()

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Головне меню"),
        BotCommand(command="order", description="Зробити замовлення"),
        BotCommand(command="cabinet", description="Мої замовлення"),
        BotCommand(command="faq", description="Часті питання"),
        BotCommand(command="prices", description="Прайс-лист"),
        BotCommand(command="feedback", description="Залишити відгук"),
        BotCommand(command="support", description="Зв'язок з менеджером"),
        BotCommand(command="help", description="Список команд")
    ]
    await bot.set_my_commands(commands)

@router.message(Command("order"))
async def order_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        await state.clear()
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=name, callback_data=f"order_type:{code}")]
                for name, code in ORDER_TYPES
            ]
        )
        await message.answer("Оберіть тип роботи:", reply_markup=keyboard)
        print(f"[INFO] /order: user {user_id} - order menu sent")
    except Exception as e:
        print(f"[ERROR] /order: user {user_id} - {e}")
        await message.answer("Сталася помилка при створенні замовлення.")

@router.message(F.text == "📝 Нове замовлення")
async def order_button_handler(message: types.Message, state: FSMContext):
    from app.handlers.order import order_handler
    await order_handler(message, state)

@router.message(F.text == "👤 Мій кабінет")
async def cabinet_button_handler(message: types.Message, state: FSMContext):
    from app.handlers.cabinet import cabinet_handler
    await cabinet_handler(message, state) 