import asyncio
import logging
import os
import sys
 
# Гарантируем что /app в sys.path (нужно для Docker)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
 
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
 
from handlers import student, teacher, common
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
 
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
API_SERVICE_URL = os.getenv("API_SERVICE_URL", "http://localhost:8000")
 
 
async def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable is not set")
 
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
 
    dp["api_url"] = API_SERVICE_URL
 
    dp.include_router(common.router)
    dp.include_router(student.router)
    dp.include_router(teacher.router)
 
    logger.info("Starting FastQueue bot...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
 
 
if __name__ == "__main__":
    asyncio.run(main())