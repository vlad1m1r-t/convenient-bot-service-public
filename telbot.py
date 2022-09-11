import telebot
import sqlite3
import requests
import datetime
from bs4 import BeautifulSoup

con = sqlite3.connect("usersbot.db", check_same_thread=False) #Подключаемся к БД где "usersbot.db" название БД
cur = con.cursor() #Для извлечения результатов SQL-запросов нам потребуется использовать курсор БД

token = 'Ваш токен' #Ваш токен Телеграмм-бота полученнный у BotFather в самом телеграмме
bot = telebot.TeleBot(token) #Создаем переменную bot для выполенения комманд ботом


@bot.message_handler(commands=['start']) #Создаем Приветствие бота по команде /start
def check_reg_users(message): #Создаем функцию проверки регистрации пользователя в БД
    info = cur.execute("SELECT chatid FROM users where chatid=?", (message.chat.id,)) #Запрашиваем в БД пользователя по chatid в таблице users
    if info.fetchone() is None: #Если пользователя нет в БД, то привествуем его начинаем вносить необходимые нам данные
        bot.send_message(message.chat.id, f'Добро пожаловать {message.from_user.first_name}! Я знаю только твоё имя. Позволь узнать другую информацию о тебе!')
        cur.execute("INSERT INTO users (chatid, name) VALUES    (?,?)", (message.chat.id, message.from_user.first_name))
        msg = bot.send_message(message.chat.id, f'Где ты живешь {message.from_user.first_name}? (Полное название города)')
        bot.register_next_step_handler(msg, reg_city) #Переходим в другую функцию чтобы внести новую информацию в БД по сообщению пользователя
        con.commit() #Обязательное обновление БД после внесенных изменений
    else: #Если пользователь зарегистрирован то просто его приветствуем
        bot.send_message(message.chat.id, f'Я тебя снова приветствую {message.from_user.first_name}!')

def reg_city(message): #Функция регистрации города пользователя в БД
    cur.execute("UPDATE users SET city=? WHERE chatid=?", (message.text, message.chat.id,))#Так запись уже создана по chatid, значит просто обновляем данные города
    con.commit() #Обязательно обновление БД после внесенных изменений
    msg1 = bot.send_message(message.chat.id, f'Всегда мечтал там побывать! Какие новости тебя интересуют? (Темы через запятую!)')
    bot.register_next_step_handler(msg1, reg_themes) #Переходим в другую функцию чтобы внести новую информацию в БД по сообщению пользователя

def reg_themes(message): #Функция регистрации города пользователя в БД
    cur.execute("UPDATE users SET themes=? WHERE chatid=?", (message.text, message.chat.id,)) #Так запись уже создана по chatid, значит просто обновляем данные тем пользователя
    con.commit() #Обязательно обновление БД после внесенных изменений
    bot.send_message(message.chat.id, f'А у нас вкусы совпадают! Приятно познакомиться.\nПопробуй у меня что-то узнать {message.from_user.first_name}???')

@bot.message_handler(commands=['weather']) #Создаем сервис Погоды по команде /weather
def get_weather(message): #Создаем функцию погоды
    open_weather_token = 'Ваш токен' #Погоду берем с сайта openweathermap по специальному токену после регистрации
    city_id = cur.execute("SELECT city FROM users WHERE chatid=?", (message.chat.id,)) #Запрашиваем город из БД пользователя
    city = [i for i in city_id.fetchone()] #Вытаскиваем город из запроса

    url = requests.get(f'http://api.openweathermap.org/geo/1.0/direct?q={city},&appid={open_weather_token}') #Обращаемся по специальной ссылки где указываем город и токен чтобы узнать координаты города
    lat = url.json()[0]['lat'] #Вытаскиваем параметр долготы
    lon = url.json()[0]['lon'] #Вытаскиваем параметр широты
    urlweather = requests.get(
        f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={open_weather_token}&units=metric') #Обращаемся по специальной ссылки где указываем параметры долго, ширины, и токен, чтобы взять данные погоды

    code_description = {
        "Clear": "Ясно \U00002600",
        "Clouds": "Облачно \U00002601",
        "Rain": "Дождь \U00002614",
        "Drizzle": "Дождь \U00002614",
        "Thunderstorm": "Гроза \U000026A1",
        "Snow": "Снег \U0001F328",
        "Mist": "Туман \U0001F32B"
    }  #Создаем эмоджи и описание погоды для красивого оформления, взяли самые главные виды погод

    weather_description = urlweather.json()["weather"][0]["main"] #Берем виды погод
    if weather_description in code_description: #Сравниваем с нашишм описанием
        wd = code_description[weather_description]
    else: #Если нет такой разновидности погоды в нашем описании, то предлагаем пользователю выглянуть в окно
        wd = 'Посмотри лучше в окно, я не понимаю что там происходит!'

    city_get = urlweather.json()["name"] #Забираем город погоды во избежании ошибок
    temp = urlweather.json()["main"]["temp"] #Забираем температуру на данный момент
    temp_max = urlweather.json()["main"]["temp_max"] #Забираем максимальную температуру на данный момент
    temp_feels_like = urlweather.json()["main"]["feels_like"] #Забираем температуру по ощущению человека
    humidity = urlweather.json()["main"]["humidity"] #Забираем влажность
    bot.send_message(message.chat.id, f'Погода в городе: {city_get}\nТемпература: {temp}°C Ошущается как: {temp_feels_like}°C, {wd}\n'
          f'Максимальная температура: {temp_max}°C\nВлажность: {humidity}%') #Отправляем пользователю погоду по его запросу


@bot.message_handler(commands=['news']) #Создаем сервис Новости по команде /news
def get_news(message): #Создаем функцию новостей
    themes = [i.split(',') for i in cur.execute("SELECT themes FROM users WHERE chatid=?", (message.chat.id,)).fetchone()] # забираем темы пользователя
    for t in range(len(themes[0])): #Создаем цикл новостей по каждой теме
        theme = themes[0][t]
        url = requests.get(f'https://newssearch.yandex.ru/news/search?text={theme}') #Отправляем запрос на поиск новостей по одной теме
        soup = BeautifulSoup(url.text, 'lxml')
        section_url = soup.find_all(class_="mg-snippet__url") #Забираем все ссылки новостей
        for i in range(5): #Создаем цикл для 5 новостей по каждой теме
            news_href = section_url[i].findNext('a', href=True) #Забираем одну ссылку из всех найденых
            bot.send_message(message.chat.id,f'[Твоя тема: {theme}]({news_href["href"]})', parse_mode='Markdown') #Отправляем пользователю

@bot.message_handler(commands=['rate']) #Создаем сервис Курс основных валют по команде /rate
def exchange_rate(message): #Создаем функцию новостей
    now = datetime.datetime.now()
    date = now.strftime('%d/%m/%Y') #Забираем сегодняшнюю дату, так как забрать данные валют с центробанка можно только по дате
    url = requests.get(f'https://cbr.ru/scripts/XML_daily.asp?date_req={date}') #Специальная ссылка для взятия курса валют: Доллара и Евро
    urlbitc = requests.get("https://www.blockchain.com/ru/ticker") #Биткоин будем брать с блокчейна
    soup = BeautifulSoup(url.text, 'lxml')
    rate_usd = soup.find(id="R01235").find('value').text #Забираем курс Доллара
    rate_eur = soup.find(id="R01239").find('value').text #Забираем курс Евро
    bot.send_message(message.chat.id, f'Курс Доллар США: {rate_usd}р 💵\nКурс Евро: {rate_eur}р 💶\nБиткоин: {urlbitc.json()["USD"]["last"]}$') #Отправляем пользователю

@bot.message_handler(commands=['update_city']) #Создаем возможность изменить город пользователя для актуальной информации о погоде
def update_city(messange):
    new_city = bot.send_message(messange.chat.id, 'Перехал(а) в другой город? Введи новый город(Полное название)')
    bot.register_next_step_handler(new_city,updatecity)
def updatecity(message):
    cur.execute("UPDATE users set city=? where chatid=?", (message.text, message.chat.id,))
    con.commit()
    bot.send_message(message.chat.id, f'Я запомнил! Теперь ты живешь в "{message.text}"')

@bot.message_handler(commands=['update_themes']) #Создаем возможность изменить темы пользователя для получения нужных пользователю новостей
def update_themes(messange):
    new_themes = bot.send_message(messange.chat.id, 'Хочешь поменять темы? Вводи через запятую!')
    bot.register_next_step_handler(new_themes,updatethemes)
def updatethemes(message):
    cur.execute("UPDATE users set themes=? where chatid=?", (message.text, message.chat.id,))
    con.commit()
    bot.send_message(message.chat.id, f'Я запомнил! Теперь ты желаешь получать новости по теме(темам) "{message.text}"')

@bot.message_handler() #Любое сообщение без команды
def dont_understand(message): #Создаем функцию которая определяет содержимое сообщения
    if 'Погод'.lower() in message.text.lower(): #Если в сообщении пользователя содержится слово ПОГОД, то выполяется сервис Погода
        get_weather(message)
    elif 'Привет'.lower() in message.text.lower(): #Если в сообщении пользователя содержится слово Привет, то проверяем пользователя зарегистрирован ли он
        check_reg_users(message)
    elif 'Новост'.lower() in message.text.lower(): #Если в сообщении пользователя содержится слово Новост, то выполяется сервис Новости
        get_news(message)
    elif 'Долл'.lower() in message.text.lower() or 'Евр'.lower() in message.text.lower() or 'Биткои'.lower() in message.text.lower() or 'Курс'.lower() in message.text.lower():
        exchange_rate(message)
    elif 'Обнови город'.lower() in message.text.lower() or 'Измени город'.lower() in message.text.lower():
        update_city(message)
    elif 'Обнови тем'.lower() in message.text.lower() or 'Измени тем'.lower() in message.text.lower():
        update_themes(message)
    else: #Если в сообщении не содержится слов для определенной команды, то бот сообщает свои возможности
        bot.send_message(message.chat.id, 'Моя твоя не понимать!')
        bot.send_message(message.chat.id, f'Знаю команды:\n'
                                          f'/start - Для тех кого я еще не запомнил😑\n'
                                          f'/weather или слово ПОГОДА - Если лень выглядывать в окно😤 и желаешь узнать погоду!☂\n'
                                          f'/news или слово НОВОСТИ  - Если желаешь почитать интересующие тебя темы которые ты мне рассказал'
                                          f' по секрету🤫\n'
                                          f'/rate или слова ВАЛЮТА,ДОЛЛАР,ЕВРО,БИТКОИН - Если желаешь узнать не уменьшились ли твои накопления😁, ну и заодно курс'
                                          f' валют👀\n'
                                          f'/update_city или ИЗМЕНИ ГОРОД, ОБНОВИ ГОРОД чтобы обновить твой город для актуальности погоды\n'
                                          f'/update_themes или ИЗМЕНИ ТЕМЫ, ОБНОВИ ТЕМЫ чтобы обновить интересующие тебя темы для актуальности новостей')



if __name__ == '__main__':
    bot.infinity_polling(none_stop=True, timeout=123, skip_pending=True)