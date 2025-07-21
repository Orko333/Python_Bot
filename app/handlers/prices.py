from aiogram import types, Router
from aiogram.filters import Command
from app.config import ORDER_TYPE_PRICES
from aiogram.fsm.context import FSMContext

router = Router()

@router.message(Command("prices"))
async def prices_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        await message.delete()
        data = await state.get_data()
        last_info_id = data.get('last_info_message_id')
        if last_info_id:
            try:
                await message.bot.delete_message(message.chat.id, last_info_id)
            except: pass
        text = "<b>Наші базові розцінки:</b>\n\n"

        for code, details in ORDER_TYPE_PRICES.items():
            label = details.get("label", "Невідомий тип")
            base_price = details.get("base", 0)
            
            price_details = f"Базова ціна: <b>{base_price} грн</b>"
            
            if "per_page" in details:
                price_details += f" + {details['per_page']} грн/сторінка."
            elif "per_work" in details:
                price_details += f" + {details['per_work']} грн/робота."

            text += f"▪️ <b>{label}</b>\n   {price_details}\n\n"

        text += "<i>*Це орієнтовні ціни. Фінальна вартість залежить від складності, термінів та особливих вимог.</i>"
        
        sent = await message.answer(text, parse_mode="HTML")
        await state.update_data(last_info_message_id=sent.message_id)
        print(f"[INFO] /prices: user {user_id} - prices sent")
    except Exception as e:
        print(f"[ERROR] /prices: user {user_id} - {e}")
        sent = await message.answer("Сталася помилка при отриманні прайсу.")
        await state.update_data(last_info_message_id=sent.message_id) 