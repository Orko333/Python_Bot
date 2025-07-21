from .start import router as start_router
from .help import router as help_router
from .order import router as order_router
from .cabinet import router as cabinet_router
from .support import router as support_router
from .feedback import router as feedback_router
from .faq import router as faq_router
from .prices import router as prices_router
from .broadcast import router as broadcast_router

# Експортуємо всі роутери для використання в bot.py
__all__ = [
    'start_router',
    'help_router',
    'order_router',
    'cabinet_router',
    'support_router',
    'feedback_router',
    'faq_router',
    'prices_router',
    'broadcast_router'
] 