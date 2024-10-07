import asyncio
import logging
import sys
from aiogram.filters import Command, CommandStart
from aiogram import Bot,types,Dispatcher, Router,F
from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton,
                           InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery)
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from models import Session, Homework #импорт моих моделей из models
from datetime import datetime, timedelta
import calendar
from aiogram.fsm.context import FSMContext
#импорт функций из database
from database import (get_all_homework,add_homework, get_homework_by_date,
                      get_homework_for_week, get_homework_for_two_weeks,
                      update_homework, get_homework_by_subject_and_deadline, delete_homework, delete_all_homework)

API_TOKEN = 'MY_TOKEN'
router = Router()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Form(StatesGroup):
    subject = State()
    task = State()
    deadline = State()
    subjectUpdate = State()
    deadlineUpdate = State()
    taskUpdate = State()
    subjectDelete = State()
    confirmDeleteAll = State()

@router.message(Command("start"))
async def start_command(message: types.Message):
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Добавить д/з")],
            [KeyboardButton(text="Получить д/з")],
            [KeyboardButton(text="Обновить д/з")],
            [KeyboardButton(text="Удалить все д/з")],
            [KeyboardButton(text="Удалить д/з")],
            [KeyboardButton(text="Отмена")]  # Кнопка отмены
        ],
        resize_keyboard=True
    )

    await message.answer("Выберите действие:", reply_markup=keyboard)
# Обработка нажатия кнопки "Отмена"
@router.message(lambda message: message.text == "Отмена")
async def cancel_button(message,state):
    await cancel_action(message,state)

# Обработка нажатия кнопки "Добавить д/з""
@router.message(lambda message: message.text == "Добавить д/з")
async def add_homework_button(message: types.Message, state: FSMContext):
    await add_homework_command(message, state)

# Обработка нажатия кнопки "Получить д/з""
@router.message(lambda message: message.text == "Получить д/з")
async def get_homework_button(message: types.Message):
    await get_homework(message)

# Обработка нажатия кнопки "Обновить д/з""
@router.message(lambda message: message.text == "Обновить д/з")
async def update_homework_button(message: types.Message, state: FSMContext):
    await update_homework_bot(message, state)

# Обработка нажатия кнопки "Удалить д/з"
@router.message(lambda message: message.text == "Удалить д/з")
async def delete_homework_button(message: types.Message,state: FSMContext):
    await delete_homework_command(message,state)

#Обработка нажатия кнопки "Удалить все д/з"
@router.message(lambda message: message.text == "Удалить все д/з")
async def delete_all_homework_button(message: types.Message,state: FSMContext):
    await delete_all_homework_command(message,state)  # Вызываем команду удаления всех домашних заданий

#Функция отмены
async def cancel_action(message,state: FSMContext):
    await state.clear()  # Очищаем состояние
    await message.answer('Выберите действие заново')

#Функция добавления д/з-----------------------------------------------
@router.message(Command("add_homework"))
async def add_homework_command(message: types.Message, state: FSMContext):
    await state.set_state(Form.subject)

    await message.answer("Введите предмет:")

@router.message(Form.subject)
async def process_subject(message: types.Message, state: FSMContext):
    subject = message.text.lower()
    await state.update_data(subject=subject)

    await state.set_state(Form.task)

    await message.answer('Введите задание:')


@router.message(Form.task)
async def process_task(message: types.Message, state: FSMContext):
    task = message.text.lower()
    await state.update_data(task=task)

    user_data = await state.get_data()
    logger.info(f"user_data = {user_data}")
    subject = user_data['subject']
    task = user_data['task']

    #Получаем текущую дату и создаем список возможных дедлайнов
    current_date = datetime.now().date()

    days_list = [(current_date + timedelta(days=i)).day for i in range(14)]
    date_list = [(current_date + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(14)]

    #Создаём список дат в формате YYYY-MM-DD для сохранения в БД
    date_list = [(current_date.replace(day=day)).strftime('%Y-%m-%-d') for day in days_list]

    await state.update_data(days_list=days_list)
    await state.update_data(date_list=date_list)
    await state.update_data(subject=subject)
    await state.update_data(task=task)
    keyboard = await inline_days_keyboard(days_list)
    await message.answer("Выберите срок сдачи:",reply_markup= keyboard)

@router.callback_query(lambda c: c.data.isdigit())
async def process_deadline_selection(callback_query: types.CallbackQuery,
                                     state: FSMContext):
    tg_id = callback_query.from_user.id

    day_selected = int(callback_query.data) #Получаем выбранный день
    user_data = await state.get_data()
    date_list = user_data['date_list']
    deadline = date_list[day_selected - 1]

    subject = user_data['subject']
    task = user_data['task']

    logger.info(f"user_data_(2) = {user_data}")

    existing_homework = get_homework_by_subject_and_deadline(subject,deadline,tg_id)
    logger.info(f"Существующая домашняя работа: {existing_homework}")

    if existing_homework:
        task_old = existing_homework[0][2]
        combined_task = f"{task_old}, {task}"
        update_homework(existing_homework[0][0],subject,
                        combined_task, deadline,tg_id)
        message = "Задание обновлено в существующей записи!"
        await callback_query.message.edit_reply_markup(reply_markup=None)
        await callback_query.message.answer(message)

    else:
        add_homework(subject,task,deadline,tg_id)
        message = "Домашнее задание добавлено!"
        await callback_query.message.edit_reply_markup(reply_markup=None)
        await callback_query.message.answer(message)



    await state.clear()

#создание клавиатуры
async def inline_days_keyboard(days_list):
    keyboard = InlineKeyboardMarkup(inline_keyboard= [])
    row = []
    for deadline in days_list:
        buttons = InlineKeyboardButton(text= f"{deadline}",
                                      callback_data=f"{int(deadline)}")
        row.append(buttons)
        if len(row) == 5:
            keyboard.inline_keyboard.append(row)
            row = []

    if row:
        keyboard.inline_keyboard.append(row)

    return keyboard


#Функция получения д/з-----------------------------------------------
@router.message(Command('get_homework'))
async def get_homework(message: types.Message):
    inline_period_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="День", callback_data="get_homework_day"),
            InlineKeyboardButton(text="Неделя", callback_data="get_homework_week")
        ],
        [
            InlineKeyboardButton(text="2 недели", callback_data="get_homework_two_weeks"),
            InlineKeyboardButton(text="За всё время", callback_data="get_all")
        ]
    ])  # Создаем клавиатуру с кнопками для выбора периода

    await message.answer("Выберите период:", reply_markup=inline_period_keyboard)  # Отправляем сообщение с клавиатурой

# Обработчик для получения домашнего задания по периоду - День
@router.callback_query(lambda c: c.data == "get_homework_day")
async def get_homework_day(callback_query: types.CallbackQuery):
    tg_id = callback_query.from_user.id
    today = datetime.now().date()
    homework = get_homework_by_date(today,tg_id)

    if homework:
        response = "\n".join([f"{h[1].capitalize()} : {h[2]} ({h[3][5:]})" for h in homework])
    else:
        response = "Нет домашних заданий на сегодня."

    await callback_query.answer()  # Подтверждаем нажатие кнопки
    await callback_query.message.answer(response)  # Отправляем ответ

# Обработчик для получения домашнего задания по периоду - Неделя
@router.callback_query(lambda c: c.data == "get_homework_week")
async def get_homework_week(callback_query: types.CallbackQuery):
    tg_id = callback_query.from_user.id
    today = datetime.now().date()
    homework = get_homework_for_week(today,  tg_id)

    if homework:
        response = "\n".join([f"{h[1].capitalize()} : {h[2]} ({h[3][5:]})" for h in homework])
    else:
        response = "Нет домашних заданий на эту неделю."

    await callback_query.answer()  # Подтверждаем нажатие кнопки
    await callback_query.message.answer(response)  # Отправляем ответ

# Обработчик для получения домашнего задания по периоду - 2 недели
@router.callback_query(lambda c: c.data == "get_homework_two_weeks")
async def get_homework_two_weeks(callback_query: types.CallbackQuery):
    tg_id = callback_query.from_user.id
    today = datetime.now().date()
    homework = get_homework_for_two_weeks(today,tg_id)

    if homework:
        response = "\n".join([f"{h[1].capitalize()} : {h[2]} ({h[3][5:]})" for h in homework])
    else:
        response = "Нет домашних заданий за следующие две недели."

    await callback_query.answer()  # Подтверждаем нажатие кнопки
    await callback_query.message.answer(response)  # Отправляем ответ

#Функция получения всех д/з
@router.callback_query(lambda c: c.data == "get_all")
async def get_all(callback_query: types.CallbackQuery):
    tg_id = callback_query.from_user.id
    homework = get_all_homework(tg_id)
    if homework:
        response = "\n".join([f"{h[1].capitalize()} : {h[2]} ({h[3][5:]})" for h in homework])
    else:
        response = "Лист домашних заданий пуст"

    await callback_query.answer()
    await callback_query.message.answer(response)


#функция обновления (редактирования) д/з
@router.message(Command('update_homework'))
async def update_homework_bot(message: types.Message, state: FSMContext):
    await state.set_state(Form.subjectUpdate)  # Установка состояния для получения предмета
    await update_subject(message, state)

@router.message(Form.subjectUpdate)
async def update_subject(message: types.Message, state: FSMContext):
    tg_id = message.from_user.id
    logger.info("Пользователь инициировал обновление предмета.")

    # Получаем все предметы домашнего задания
    homework_list = get_all_homework(tg_id)
    logger.info(f"Доступный список домашних заданий: {homework_list}")


    if not homework_list:
        await message.answer("Нет доступных предметов для обновления.")
        return

    # Создаем инлайн-клавиатуру для предметов
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for homework in homework_list:
        subject_name = homework[1]
        deadline = homework[3]  # Предполагается, что дедлайн находится в 4-й колонке

        # Преобразуем строку даты в объект datetime и форматируем
        deadline_date = datetime.strptime(deadline, "%Y-%m-%d")
        formatted_deadline = deadline_date.strftime("%-d %B")
        button_text = f"{subject_name.capitalize()}  ({deadline[5:]})"  # Формируем текст кнопки

        button = InlineKeyboardButton(text=button_text, callback_data=f"subject:{subject_name}:{deadline}")
        keyboard.inline_keyboard.append([button])  # Добавляем кнопку в новую строку

    await state.update_data(homework_list=homework_list)
    await message.answer("Пожалуйста, выберите предмет из списка:", reply_markup=keyboard)


#Обработчик кнопок предмета
@router.callback_query(lambda c: c.data.startswith('subject:'))
async def process_subject_selection(callback_query: types.CallbackQuery, state: FSMContext):
    data = callback_query.data.split(":")
    subjectUpdate = data[1]
    deadline = data[2]

    user_data = await state.get_data()
    homework_list = user_data.get('homework_list',[])
    homework_to_update = [h for h in homework_list if h[1].lower() == subjectUpdate]
    matching_homework = [h for h in homework_to_update if h[3] == deadline]
    logger.info(f"Выбранный предмет: {subjectUpdate}, Дедлайн: {deadline}")

    # Сохраняем выбранный предмет и дедлайн в состоянии
    await state.update_data(selected_subject=subjectUpdate)
    await state.update_data(selected_deadline=deadline)
    await callback_query.message.answer(f"Введите новое задание для {subjectUpdate} с дедлайном {deadline}:")

    await state.update_data(matching_homework=matching_homework)
    await state.update_data(homework_to_update=homework_to_update)

    # Меняем состояние на обновление задания
    await state.set_state(Form.taskUpdate)



@router.message(Form.taskUpdate)
async def update_task(message: types.Message,state: FSMContext):
    tg_id = message.from_user.id
    user_data = await state.get_data()

    logger.info(f"user_data: {user_data}")

    subjectUpdate = user_data['selected_subject']
    deadline = user_data['selected_deadline']
    homework_to_update = user_data.get('homework_to_update',[])


    new_task = message.text

    for homework in homework_to_update:
        homework_id = homework[0] #Получаем ID д/з

        # Обновление д/з в БД
        update_homework(homework_id, subjectUpdate, new_task, deadline,tg_id)

    await message.answer(f"Все д/з по предмету {subjectUpdate} обновлены")
    await state.clear()

#Удаление всех д/з по предмету
@router.message(Command('delete_homework'))
async def delete_homework_command(message: types.Message,state: FSMContext):
    await message.answer("Введите предмет, домашнее задание для которого хотите удалить:")

    await state.set_state(Form.subjectDelete) #установка состояния для получения предмета

@router.message(Form.subjectDelete)
async def process_delete_subject(message: types.Message,state: FSMContext):
    tg_id = message.from_user.id
    subjectDelete = message.text

    #получаем все д/з с указанным предметом
    homework_list = get_all_homework(tg_id) #получаем все задания
    logger.info(f"Лист домашних заданий: {homework_list}")
    homework_to_delete = [h for h in homework_list if h[1].lower() == subjectDelete.lower()] #фильтр по предмету

    if not homework_to_delete:
        await message.answer("Нет домашних заданий с таким предметом. Пожалуйста, проверьте правильность ввода.")
        await state.set_state(Form.subjectDelete)  # Устанавливаем состояние для повторного ввода
        return #явное завершение функции

    #Удаление всех найденных заданий
    for homework in homework_to_delete:
        delete_homework(homework[0],tg_id)

    await message.answer(f"Все домашние задания по предмету {subjectDelete} удалены")
    await state.clear()

#Удаление всех домашних заданий
@router.message(Command('delete_all_homework'))
async def delete_all_homework_command(message: types.Message, state: FSMContext):
    inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Да", callback_data="confirm_delete_all_yes"),
            InlineKeyboardButton(text="Нет", callback_data="confirm_delete_all_no")
        ]
    ])

    await message.answer("Точно ли вы хотите очистить лист домашних заданий?\nДанные невозможно восстановить!", reply_markup=inline_keyboard)
    await state.set_state(Form.confirmDeleteAll)  # Устанавливаем состояние для подтверждения

# Обработчик подтверждения удаления - "Да"
@router.callback_query(lambda c: c.data == "confirm_delete_all_yes")
async def confirm_delete_all_yes(callback_query: types.CallbackQuery, state: FSMContext):
    tg_id = callback_query.from_user.id
    delete_all_homework(tg_id)  # Вызываем функцию удаления всех домашних заданий
    await callback_query.answer()  # Подтверждаем нажатие кнопки
    await callback_query.message.answer("Все домашние задания были успешно удалены.")
    await state.clear()  # Очищаем состояние после завершения действия

# Обработчик подтверждения удаления - "Нет"
@router.callback_query(lambda c: c.data == "confirm_delete_all_no")
async def confirm_delete_all_no(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()  # Подтверждаем нажатие кнопки
    await callback_query.message.answer("Удаление отменено.")
    await state.clear()  # Очищаем состояние после завершения действия


async def main():
    bot = Bot(token=API_TOKEN)
    dp = Dispatcher()

    dp.include_router(router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    logger.info("Запуск бота...")
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
