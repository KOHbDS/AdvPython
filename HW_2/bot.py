import asyncio
from aiogram import Bot, Dispatcher
from config import TOKEN
from routers import base_handlers, logged_handlers, user_handlers


bot = Bot(token=TOKEN)
dp = Dispatcher()
dp.include_routers(
    base_handlers.router, 
    user_handlers.router, 
    logged_handlers.router
    )

async def main():
    print('bot is start')
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())