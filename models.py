from sqlalchemy import create_engine, Column, Integer, String,Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Homework(Base):
    __tablename__ = 'homework' #имя каталога
    id = Column(Integer, primary_key=True) #создание столбца с уникальным id
    subject = Column(String) #название предмета (Строчный тип)
    task = Column(String)
    deadline = Column(Date)
    telegram_id = Column(Integer)  # Telegram ID пользователя

engine = create_engine('sqlite:///homework.db') #подключение к базе данных
Base.metadata.create_all(engine) #создание таблицы
Session = sessionmaker(bind=engine) #создание класса сессий для управления оп-циями с бд

