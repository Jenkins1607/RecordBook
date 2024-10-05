import sqlite3
from datetime import datetime,timedelta

#Функция для создания или подключения к базе данных
def create_connection(db_file):
    conn = sqlite3.connect(db_file)
    return conn

#Функция для создания таблицы
def create_table():
    conn = create_connection('homework.db')
    cursor = conn.cursor()
    cursor.execute( '''
    CREATE TABLE IF NOT EXISTS homework (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject TEXT NOT NULL,
    task TEXT NOT NULL,
    deadline DATE NOT NULL,
    telegram_id INTEGER NOT NULL        
    )
    ''')
    conn.commit() #сохранения всех изменений, сделанных в текущей транзакции, в базе данных
    conn.close() #закрытие соединения с бд для экономии ресурсов


#Функция для добавления домашнего задания
def add_homework(subject,task,deadline,telegram_id):
    conn = create_connection('homework.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO homework (subject, task, deadline, telegram_id) VALUES (?, ?, ?, ?)',
                   (subject, task, deadline, telegram_id))
    conn.commit()
    conn.close()


#функция для получения всех д/з
def get_all_homework(telegram_id):
    conn = create_connection('homework.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM homework WHERE telegram_id = ?', (telegram_id,))
    results = cursor.fetchall()
    conn.close()
    return results

#Функция для обновления д/з
def update_homework(homework_id,subject,task,deadline,telegram_id):
    conn = create_connection('homework.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE homework SET subject = ?, task = ?, deadline = ? WHERE id = ? AND telegram_id = ?',
                   (subject,task,deadline,homework_id,telegram_id))
    conn.commit()
    conn.close()


#Функция для удаления домашего задания
def delete_homework(homework_id,telegram_id):
    conn = create_connection('homework.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM homework WHERE id = ? AND telegram_id = ?',
                   (homework_id,telegram_id))
    conn.commit()
    conn.close()
#Удаление всех домашних заданий
def delete_all_homework(telegram_id):
    conn = create_connection('homework.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM homework WHERE telegram_id = ?',(telegram_id,))
    conn.commit()
    conn.close()

#Функция для получения д/з за определенную дату
def get_homework_by_date(date,telegram_id):
    conn = create_connection('homework.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM homework WHERE deadline = ? AND telegram_id = ?', (date, telegram_id)) #выбираем все столбцы бд с дедлайном date
    results = cursor.fetchall() #извлекаем строки из бд с нашей date
    conn.close()
    return results

#Функция для получения д/з за неделю
def get_homework_for_week(start_date,telegram_id):
    conn = create_connection('homework.db')
    cursor = conn.cursor()
    end_date = start_date + timedelta(days = 7)
    cursor.execute('SELECT* FROM homework WHERE deadline BETWEEN ? AND ? AND telegram_id = ?',
                   (start_date,end_date,telegram_id))
    results = cursor.fetchall()
    conn.close()
    return results


#Функция для получения д/з за две недели
def get_homework_for_two_weeks(start_date,telegram_id):
    conn = create_connection('homework.db')
    cursor = conn.cursor()
    end_date = start_date + timedelta(days = 14)
    cursor.execute('SELECT* FROM homework WHERE deadline BETWEEN ? AND ? AND telegram_id = ?',
                   (start_date,end_date,telegram_id))
    results = cursor.fetchall()
    conn.close()
    return results

#Функция для сравнения данных(предмет и дедлайн),
#введенных пользователем с уже существующими строками в БД
def get_homework_by_subject_and_deadline(subject, deadline,telegram_id):
    conn = create_connection('homework.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM homework WHERE subject = ? AND deadline = ? AND telegram_id = ?',
                   (subject, deadline, telegram_id))
    result = cursor.fetchall()
    conn.close()
    return result


create_table()  # Создаем новую таблицу






