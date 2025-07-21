from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from app.config import Config
from app.db import get_orders # We use get_orders to get all users who ever ordered

router = Router()

class BroadcastStates(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirmation = State()

@router.message(Command("broadcast"))
async def broadcast_start_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        if user_id not in Config.ADMIN_IDS:
            print(f"[ERROR] /broadcast: user {user_id} - not admin")
            return
        await message.delete()
        prompt_message = await message.answer("Введіть текст повідомлення для розсилки:")
        await state.update_data(last_bot_message_id=prompt_message.message_id)
        await state.set_state(BroadcastStates.waiting_for_message)
        print(f"[INFO] /broadcast: admin {user_id} - started broadcast")
    except Exception as e:
        print(f"[ERROR] /broadcast: user {user_id} - {e}")
        await message.answer("Сталася помилка при старті розсилки.")

@router.message(BroadcastStates.waiting_for_message)
async def broadcast_message_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_bot_message_id = data.get('last_bot_message_id')
    
    if last_bot_message_id:
        try:
            await message.bot.delete_message(message.chat.id, last_bot_message_id)
        except: pass
    try:
        await message.delete()
    except: pass
        
    await state.update_data(message_text=message.text)
    
    orders = get_orders()
    user_ids = set(order[1] for order in orders) # Assuming user_id is at index 1
    
    await state.update_data(user_ids_to_send=list(user_ids))
    
    prompt_message = await message.answer(
        f"Повідомлення для розсилки:\n\n---\n{message.text}\n---\n\n"
        f"Знайдено {len(user_ids)} унікальних користувачів для розсилки. "
        f"Надіслати? (так/ні)",
    )
    await state.update_data(last_bot_message_id=prompt_message.message_id)
    await state.set_state(BroadcastStates.waiting_for_confirmation)

@router.message(BroadcastStates.waiting_for_confirmation)
async def broadcast_confirmation_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    last_bot_message_id = data.get('last_bot_message_id')
    
    if last_bot_message_id:
        try:
            await message.bot.delete_message(message.chat.id, last_bot_message_id)
        except: pass
    try:
        await message.delete()
    except: pass

    if message.text.lower() not in ["так", "yes"]:
        await message.answer("Розсилку скасовано.")
        await state.clear()
        return

    user_ids = data.get("user_ids_to_send", [])
    message_text = data.get("message_text", "")
    
    if not user_ids or not message_text:
        await message.answer("Немає користувачів або тексту для розсилки. Скасовано.")
        await state.clear()
        return

    await message.answer(f"Починаю розсилку для {len(user_ids)} користувачів...")
    
    successful_sends = 0
    failed_sends = 0

    for user_id in user_ids:
        try:
            await message.bot.send_message(user_id, message_text, parse_mode="HTML")
            successful_sends += 1
        except Exception:
            failed_sends += 1
            
    await message.answer(
        f"Розсилку завершено.\n\n"
        f"✅ Успішно надіслано: {successful_sends}\n"
        f"❌ Не вдалося надіслати: {failed_sends}"
    )
    await state.clear() 