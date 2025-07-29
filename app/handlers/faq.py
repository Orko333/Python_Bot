from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
from aiogram.fsm.context import FSMContext
from app.utils.validation import is_command
from app.db import log_message

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

FAQ_DATA = {
    "guarantees": {
        "question": "Які гарантії?",
        "answer": "Ми гарантуємо унікальність кожної роботи та її відповідність вашим вимогам. Усі роботи проходять перевірку на плагіат. Якщо будуть потрібні правки, ми внесемо їх безкоштовно протягом гарантійного періоду."
    },
    "payment": {
        "question": "Як відбувається оплата?",
        "answer": "Оплата відбувається у два етапи: 50% передоплати для початку роботи та 50% після того, як робота буде готова. Реквізити для оплати вам надасть менеджер."
    },
    "revisions": {
        "question": "Що робити, якщо потрібні правки?",
        "answer": "Якщо вам або вашому викладачу знадобляться правки, ми внесемо їх безкоштовно. Просто повідомте про це вашого менеджера та надайте список необхідних змін."
    },
    "deadlines": {
        "question": "Які терміни виконання?",
        "answer": "Стандартний термін виконання курсової роботи – від 7 до 14 днів. Однак ми можемо виконати роботу і в коротші терміни за додаткову плату. Усі терміни обговорюються індивідуально."
    },
    "privacy": {
        "question": "Чи конфіденційно це?",
        "answer": "Так, ми гарантуємо повну конфіденційність. Ваші особисті дані та деталі замовлення ніколи не будуть передані третім особам. Детальніше ви можете прочитати в розділі /privacy."
    }
}

def get_faq_keyboard():
    buttons = [
        [InlineKeyboardButton(text=item["question"], callback_data=f"faq:{key}")]
        for key, item in FAQ_DATA.items()
    ]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

@router.message(Command("faq"))
async def faq_handler(message: types.Message, state: FSMContext):
    try:
        sent = await message.answer("Часті запитання:", reply_markup=get_faq_keyboard())
        await state.update_data(last_bot_message_id=sent.message_id)
        print(f"[INFO] /faq: user {user_id} - faq sent")
        log_message(user_id, message.from_user.username, 'user', message.text, message.chat.id)
    except Exception as e:
        print(f"[ERROR] /faq: user {user_id} - {e}")
        sent = await message.answer("Вибачте, сталася помилка. Спробуйте пізніше.")
        await state.update_data(last_bot_message_id=sent.message_id)

@router.callback_query(F.data == 'faq:back')
async def faq_back_callback(callback: types.CallbackQuery, state: FSMContext):
    try:
        keyboard = get_faq_keyboard()
        chat_id = callback.message.chat.id
        user_id = callback.from_user.id
        logger.info(f"[FAQ BACK] chat_id={chat_id}, user_id={user_id}, callback.data={callback.data}")
        await state.update_data(last_info_message_id=None)
        sent = await callback.bot.send_message(chat_id, "Часті запитання:", reply_markup=keyboard, parse_mode="HTML")
        logger.info(f"[FAQ BACK] Sent new FAQ message after back, message_id={sent.message_id}")
        await state.update_data(last_info_message_id=sent.message_id)
        await callback.answer()
        log_message(user_id, callback.from_user.username, 'user', callback.data, callback.message.chat.id)
    except Exception as e:
        logger.error(f"Error in FAQ back callback: {str(e)}")
        await callback.bot.send_message(callback.message.chat.id, f"Вибачте, сталася помилка. {e}")

@router.callback_query(lambda c: c.data and c.data.startswith('faq:'))
async def faq_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(last_info_message_id=None)
    if is_command(getattr(callback, 'data', '')):
        await state.clear()
        return
    logger.info(f"FAQ callback handler called with data: {callback.data}")
    try:
        key = callback.data.split(":")[1]
        if key in FAQ_DATA:
            answer = FAQ_DATA[key]["answer"]
            back_button = InlineKeyboardButton(text="⬅️ Назад до питань", callback_data="faq:back")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[back_button]])
            sent = await callback.message.answer(answer, parse_mode="HTML", reply_markup=keyboard)
            await state.update_data(last_bot_message_id=sent.message_id)
            logger.info(f"FAQ answer sent for key: {key}")
            log_message(callback.from_user.id, callback.from_user.username, 'user', callback.data, callback.message.chat.id)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in FAQ callback handler: {str(e)}")
        sent = await callback.message.answer("Вибачте, сталася помилка. Спробуйте пізніше.")
        await state.update_data(last_bot_message_id=sent.message_id) 