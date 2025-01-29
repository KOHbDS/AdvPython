from aiogram.fsm.state import StatesGroup, State
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, StateFilter
from datetime import datetime, timedelta
from aiogram.fsm.context import FSMContext
import random

router = Router()

users_data = {}

class Form(StatesGroup):
    name = State()
    weight  = State()
    height  = State()
    age  = State()
    activity  = State()
    city  = State()
    goal_calories  = State()

@router.message(StateFilter(None), Command('set_profile'))
async def start_form(message: Message, state: FSMContext):
    await message.reply('Как вас зовут?')
    await state.set_state(Form.name)
    #print(Form)


@router.message(Form.name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.reply('Сколько вам лет?')
    await state.set_state(Form.age)

@router.message(Form.age)
async def process_age(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.reply('Введите ваш вес (в кг):')
    await state.set_state(Form.weight)

@router.message(Form.weight)
async def process_weight(message: Message, state: FSMContext):
    await state.update_data(weight=message.text)
    await message.reply('Введите ваш рост (в см):')
    await state.set_state(Form.height)

@router.message(Form.height)
async def process_height(message: Message, state: FSMContext):
    await state.update_data(height=message.text)
    await message.reply('Сколько минут активности у вас в день?')
    await state.set_state(Form.activity)

@router.message(Form.activity)
async def process_activity(message: Message, state: FSMContext):
    await state.update_data(activity=message.text)
    await message.reply('В каком городе вы находитесь?')
    await state.set_state(Form.city)
    
@router.message(Form.city)
async def process_city(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data.get('name')
    weight = int(data.get('weight'))
    height = int(data.get('height'))
    age = int(data.get('age'))
    activity = int(data.get('activity'))
    city = message.text
    
    users_data.update({message.from_user.id : {
        'name': name,
        'weight': weight,
        'height': height,
        'age': age,
        'activity': activity,
        'city': city,
    }})
    
    

    water_goal = weight * 30
    calorie_goal = 10 * weight + 6.25 * height - 5 * age
    users_data[message.from_user.id].update({
        'water_goal' : water_goal,
        'calorie_goal' : calorie_goal,
        'logs' : {
            datetime.now().date().__str__() : {
            'date': datetime.now().date(),
            'weather_temp': 20,
            'logged_water': 0,
            'logged_activity': 0,
            'logged_calories': 0,
            'burned_calories': 0
    }}})
    
    # нужно для Графика
    for i in range(366):
        logged_water = random.randint(2500, 6000)
        logged_activity = random.randint(30, 120)
        logged_calories = random.randint(1500, 2500)
        burned_calories = logged_activity * 8
        users_data[message.from_user.id]['logs'].update({
            (datetime(2024, 1, 28) + timedelta(days=i)).date().__str__() : {
            'date': datetime(2024, 1, 28) + timedelta(days=i),
            'weather_temp': 20,
            'logged_water': logged_water,
            'logged_activity': logged_activity,
            'logged_calories': logged_calories,
            'burned_calories': burned_calories
            }
                })
    
    await message.reply(
        f"Профиль установлен! \n Привет {name}: \n"
        f"Норма воды: {water_goal+ (500 * (activity // 30))} мл;\n"
        f"Норма калорий: {calorie_goal} ккал.")
    await state.clear()

