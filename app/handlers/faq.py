from aiogram import types, Router
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging
from aiogram.fsm.context import FSMContext

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
    user_id = message.from_user.id
    try:
        await message.delete()
        data = await state.get_data()
        last_info_id = data.get('last_info_message_id')
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        keyboard = get_faq_keyboard()
        sent = await message.answer("Часті запитання:", reply_markup=keyboard)
        await state.update_data(last_info_message_id=sent.message_id)
        print(f"[INFO] /faq: user {user_id} - faq sent")
    except Exception as e:
        print(f"[ERROR] /faq: user {user_id} - {e}")
        await message.answer("Вибачте, сталася помилка. Спробуйте пізніше.")

@router.callback_query(lambda c: c.data and c.data.startswith('faq:'))
async def faq_callback_handler(callback: types.CallbackQuery, state: FSMContext):
    logger.info(f"FAQ callback handler called with data: {callback.data}")
    try:
        key = callback.data.split(":")[1]
        if key in FAQ_DATA:
            answer = FAQ_DATA[key]["answer"]
            back_button = InlineKeyboardButton(text="⬅️ Назад до питань", callback_data="faq:back")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[back_button]])
            await callback.message.edit_text(answer, parse_mode="HTML", reply_markup=keyboard)
            await state.update_data(last_info_message_id=callback.message.message_id)
            logger.info(f"FAQ answer sent for key: {key}")
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in FAQ callback handler: {str(e)}")
        await callback.message.answer("Вибачте, сталася помилка. Спробуйте пізніше.")

@router.callback_query(lambda c: c.data and c.data == 'faq:back')
async def faq_back_callback(callback: types.CallbackQuery, state: FSMContext):
    try:
        keyboard = get_faq_keyboard()
        await callback.message.edit_text("Часті запитання:", reply_markup=keyboard)
        await state.update_data(last_info_message_id=callback.message.message_id)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in FAQ back callback: {str(e)}")
        await callback.message.answer("Вибачте, сталася помилка.") 