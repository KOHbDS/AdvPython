from aiogram import Router
from aiogram.types import Message, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from routers.user_handlers import users_data
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

router = Router()


@router.message(Command('start'))
async def cmd_start(message: Message):
    await message.reply('Ну привет')


@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.reply(
        'Доступные команды:\n'
        '/set_profile - устанавливает профиль пользователя'
        '/progress - показывает текущие параметры\n'
        '/global_progress - строит график ваших успехов\n'
        '/log_water - вносит информацию по выпитой воде в формате \
            "/log_water <количество> мл"\n'
        '/log_food - вносит информацию по питанию (EN) в формате \
            "/log_food <продукт>, <количество> г"\n'
        '/log_workout - вносит информацию о тренировках в формате \
            "/log_workout <вид тренировки>, <время тренировки> мин"\n'
    )

@router.message(Command('progress'))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    today = datetime.now().date().__str__()
    #Вода
    bias_activity = users_data[user_id]['logs'][today]\
        .get('logged_activity') / 30 * 500
    bias_weather = (users_data[user_id]['logs'][today]\
        .get('weather_temp', 20) > 25 ) * 1000
    water_goal = users_data[user_id]['water_goal'] + bias_activity + bias_weather
    remaining_water = water_goal - users_data[user_id]['logs'][today].get('logged_water')
    quantity_water = users_data[user_id]['logs'][today]['logged_water']
    
    #ккал
    quantity_kkal = users_data[user_id]['logs'][today]['logged_calories']
    kkal_goal = users_data[user_id]['calorie_goal']
    burned_kkal = users_data[user_id]['logs'][today]['burned_calories']
    await message.reply(
        'Прогресс:\n'
        f'Вода:\n- Выпито: {quantity_water} мл из {water_goal} мл.\n- Осталось: {remaining_water} мл.\n\n'
        f'Калории:\n- Потреблено: {quantity_kkal} ккал из {kkal_goal} ккал.\n- Сожжено: {burned_kkal} ккал.'
    )


@router.message(Command('global_progress'))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    df = pd.DataFrame.from_dict(users_data[user_id]['logs'], orient='index')
    df.date = pd.to_datetime(df.date)
    df = df.set_index('date').sort_index()
    
    fig, axs = plt.subplots(3, 1, figsize=(6, 12))
    plt.subplots_adjust(hspace=0.5)
    df.logged_water.rolling(7).mean().plot(ax=axs[0], title='logged_water')
    df.logged_activity.rolling(7).mean().plot(ax=axs[1], title='logged_activity')
    df.logged_calories.rolling(7).mean().plot(ax=axs[2], title='logged_calories')
    fig.savefig(f"{user_id}_global_progress.png")
    g = FSInputFile(f"{user_id}_global_progress.png")
    await message.reply_photo(g)

