from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime
from aiogram.fsm.context import FSMContext
import re
from routers.user_handlers import users_data
from config import NUT_API_KEY, NUT_API_ID
import requests

router = Router()

@router.message(Command('log_water'))
async def log_water(message: Message):
    user_id = message.from_user.id
    if user_id not in users_data:
        await message.answer("Сначала настройте профиль с командой /set_profile.")
        return
    today = datetime.now().date().__str__()
    try:
        if today not in users_data[user_id]['logs']:
            users_data[user_id]['logs'].update({today: {
                'date': datetime.now().date(),
                'weather_temp': 20, # добавить актуальную температуру на день
                'logged_activity': 0,
                'logged_water': 0,
                'logged_calories': 0,
                'burned_calories': 0
            }})
        
        quantity = int(re.search(r'\d+', message.text).group())
        users_data[user_id]['logs'][today]['logged_water'] += quantity
        bias_activity = users_data[user_id]['logs'][today]\
            .get('logged_activity') / 30 * 500
        bias_weather = (users_data[user_id]['logs'][today]\
            .get('weather_temp', 20) > 25 ) * 1000
        remaining = (
            users_data[user_id]['water_goal'] + bias_activity - bias_weather 
            - users_data[user_id]['logs'][today].get('logged_water'))
        
        await message.answer(
            f"Сегодня вы выпили {users_data[user_id]['logs'][today]['logged_water']} мл воды. "
            f"Осталось {remaining} мл до цели c учетом вашей активности.")
    except (IndexError, ValueError):
        await message.answer("Используйте: /log_water <количество> мл")


@router.message(Command('log_food'))
async def log_water(message: Message):
    user_id = message.from_user.id
    if user_id not in users_data:
        await message.answer("Сначала настройте профиль с командой /set_profile.")
        return
    today = datetime.now().date().__str__()
    
    try:
        if today not in users_data[user_id]['logs']:
            users_data[user_id]['logs'].update({today: {
                'date': datetime.now().date(),
                'weather_temp': 20,
                'logged_activity': 0,
                'logged_water': 0,
                'logged_calories': 0,
                'burned_calories': 0
            }})
        food_type, q_food = tuple(message.text.split(','))
        food_type = food_type.strip()
        q_food = int(re.search(r'\d+', q_food).group()) / 100
        query = f'https://trackapi.nutritionix.com/v2/search/instant?query={food_type}'
        headers = {
                    "Content-Type": "application/json",
                    "x-app-id": NUT_API_ID,
                    "x-app-key": NUT_API_KEY
                }

        nut_food = requests.get(
            query,  
            headers=headers
            ).json()['branded'][0]['nf_calories']
        users_data[user_id]['logs'][today]['logged_calories'] += nut_food * q_food
        
        if (users_data[user_id]['calorie_goal'] 
            - users_data[user_id]['logs'][today]['logged_calories']) > 0:
            remaining = (
                users_data[user_id]['logs'][today]['logged_calories'] 
                - users_data[user_id]['calorie_goal']
                )
            await message.answer(
                f"Сегодня вы потребили {users_data[user_id]['logs'][today]['logged_calories']} ккал. "
                f"Осталось {remaining} ккал на сегодня с учетом вашей активности."
                )
        else:
            remaining = (
                users_data[user_id]['logs'][today]['logged_calories'] 
                - users_data[user_id]['calorie_goal']
                )
            await message.answer(
                f"Сегодня вы потребили {users_data[user_id]['logs'][today]['logged_calories']} ккал."
                f"Лимит на сегодня превышен на {-remaining} ккал.")
    except (IndexError, ValueError):
        await message.answer("Используйте: /log_food <продукт>, <количество> г")


@router.message(Command('log_workout'))
async def log_water(message: Message):
    user_id = message.from_user.id
    if user_id not in users_data:
        await message.answer("Сначала настройте профиль с командой /set_profile.")
        return
    today = datetime.now().date().__str__()
    try:
        if today not in users_data[user_id]['logs']:
            users_data[user_id]['logs'].update({today: {
                'date': datetime.now().date(),
                'weather_temp': 20,
                'logged_activity': 0,
                'logged_water': 0,
                'logged_calories': 0,
                'burned_calories': 0
            }})
        activites, time = tuple(message.text.split(','))
        users_data[user_id]['logs'][today]['logged_activity'] += int(time)
        users_data[user_id]['logs'][today]['burned_calories'] += int(time) * 8
        await message.answer(
                f"Сегодня у вас {users_data[user_id]['logs'][today]['logged_activity']} мин активности. "
                f"Сожжено {users_data[user_id]['logs'][today]['burned_calories']} ккал."
                )
    except (IndexError, ValueError):
        await message.answer("Используйте: /log_workout <вид тренировки>, <время тренировки> мин")