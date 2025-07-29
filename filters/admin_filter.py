# app/filters/admin_filter.py
from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from typing import Union
from app.config import Config

class IsAdmin(Filter):
    """
    Фільтр для перевірки, чи є користувач адміністратором.
    Працює як для повідомлень, так і для колбек-запитів.
    """
    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        return event.from_user.id in Config.ADMIN_IDS