import os.path
import shutil
from pprint import pprint

import telebot
import sqlite3
import requests
import datetime
from bs4 import BeautifulSoup
from pytube import YouTube

con = sqlite3.connect("usersbot.db", check_same_thread=False)
cur = con.cursor()

token = 'Ваш токен'
bot = telebot.TeleBot(token)
@bot.message_handler(commands=['start'])
def check_reg_users(message):
    info = cur.execute("SELECT chatid FROM users where chatid=?", (message.chat.id,))
    if info.fetchone() is None:
        bot.send_message(message.chat.id, f'Добро пожаловать {message.from_user.first_name}! Я знаю только твоё имя. Позволь узнать другую информацию о тебе!')
        cur.execute("INSERT INTO users (chatid, name) VALUES    (?,?)", (message.chat.id, message.from_user.first_name))
        msg = bot.send_message(message.chat.id, f'Где ты живешь {message.from_user.first_name}? (Полное название города)')
        bot.register_next_step_handler(msg, reg_city)
        con.commit()
    else:
        bot.send_message(message.chat.id, f'Я тебя снова приветствую {message.from_user.first_name}!')

def reg_city(message):
    cur.execute("UPDATE users SET city=? WHERE chatid=?", (message.text, message.chat.id,))
    con.commit()
    msg1 = bot.send_message(message.chat.id, f'Всегда мечтал там побывать! Какие новости тебя интересуют? (Темы через запятую!)')
    bot.register_next_step_handler(msg1, reg_themes)

def reg_themes(message):
    cur.execute("UPDATE users SET themes=? WHERE chatid=?", (message.text, message.chat.id,))
    con.commit()
    bot.send_message(message.chat.id, f'А у нас вкусы совпадают! Приятно познакомиться.\nПопробуй у меня что-то узнать {message.from_user.first_name}???')

@bot.message_handler(commands=['weather'])
def get_weather(message):
    open_weather_token = 'Ваш токен'
    city_id = cur.execute("SELECT city FROM users WHERE chatid=?", (message.chat.id,))
    city = [i for i in city_id.fetchone()]

    url = requests.get(f'http://api.openweathermap.org/geo/1.0/direct?q={city},&appid={open_weather_token}')
    lat = url.json()[0]['lat']
    lon = url.json()[0]['lon']
    urlweather = requests.get(
        f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={open_weather_token}&units=metric')

    code_description = {
        "Clear": "Ясно \U00002600",
        "Clouds": "Облачно \U00002601",
        "Rain": "Дождь \U00002614",
        "Drizzle": "Дождь \U00002614",
        "Thunderstorm": "Гроза \U000026A1",
        "Snow": "Снег \U0001F328",
        "Mist": "Туман \U0001F32B"
    }

    weather_description = urlweather.json()["weather"][0]["main"]
    if weather_description in code_description:
        wd = code_description[weather_description]
    else:
        wd = 'Посмотри лучше в окно, я не понимаю что там происходит!'

    city_get = urlweather.json()["name"]
    temp = urlweather.json()["main"]["temp"]
    temp_max = urlweather.json()["main"]["temp_max"]
    temp_feels_like = urlweather.json()["main"]["feels_like"]
    humidity = urlweather.json()["main"]["humidity"]
    bot.send_message(message.chat.id, f'Погода в городе: {city_get}\nТемпература: {temp}°C Ошущается как: {temp_feels_like}°C, {wd}\n'
          f'Максимальная температура: {temp_max}°C\nВлажность: {humidity}%')


@bot.message_handler(commands=['news'])
def get_news(message):
    token_news = 'Ваш токен'
    now = datetime.datetime.now()
    date = now.strftime('%Y-%m-%d')
    themes = [i.split(',') for i in cur.execute("SELECT themes FROM users WHERE chatid=?", (message.chat.id,)).fetchone()]
    for t in range(len(themes[0])):
        theme = themes[0][t]
        url = requests.get(f'https://newsapi.org/v2/everything?q={theme}&from={date}&sortBy=popularity&apiKey={token}').json()
        status = url['status']
        if status == 'ok':
            for i in range(url['totalResults']):
                news_href = url['articles'][i]['url']
                bot.send_message(message.chat.id, f"[-{url['articles'][i]['title']}]({news_href})", parse_mode='Markdown')

@bot.message_handler(commands=['rate'])
def exchange_rate(message):
    now = datetime.datetime.now()
    date = now.strftime('%d/%m/%Y')
    url = requests.get(f'https://cbr.ru/scripts/XML_daily.asp?date_req={date}')
    urlbitc = requests.get("https://www.blockchain.com/ru/ticker")
    soup = BeautifulSoup(url.text, 'lxml')
    rate_usd = soup.find(id="R01235").find('value').text.split(',')[0]
    rate_eur = soup.find(id="R01239").find('value').text.split(',')[0]
    bot.send_message(message.chat.id, f'Курс Доллар США: {rate_usd}р 💵\nКурс Евро: {rate_eur}р 💶\nБиткоин: {urlbitc.json()["USD"]["last"]}$')

@bot.message_handler(commands=['update_city'])
def update_city(messange):
    new_city = bot.send_message(messange.chat.id, 'Перехал(а) в другой город? Введи новый город(Полное название)')
    bot.register_next_step_handler(new_city,updatecity)
def updatecity(message):
    cur.execute("UPDATE users set city=? where chatid=?", (message.text, message.chat.id,))
    con.commit()
    bot.send_message(message.chat.id, f'Я запомнил! Теперь ты живешь в "{message.text}"')

@bot.message_handler(commands=['update_themes'])
def update_themes(messange):
    new_themes = bot.send_message(messange.chat.id, 'Хочешь поменять темы? Вводи через запятую!')
    bot.register_next_step_handler(new_themes,updatethemes)
def updatethemes(message):
    cur.execute("UPDATE users set themes=? where chatid=?", (message.text, message.chat.id,))
    con.commit()
    bot.send_message(message.chat.id, f'Я запомнил! Теперь ты желаешь получать новости по теме(темам) "{message.text}"')

def get_audio(message):
    yt = YouTube(message.text)
    video = yt.streams.filter(only_audio=True).first()
    out_file = video.download(output_path='audiomp/')
    base, ext = os.path.splitext(out_file)
    new_file = base + '.mp3'
    os.rename(out_file,new_file)
    audio = open(r'{a}'.format(a=new_file), 'rb')
    bot.send_chat_action(message.chat.id, 'upload_audio')
    bot.send_audio(message.chat.id, audio)
    audio.close()
    shutil.rmtree('audiomp/')

@bot.message_handler()
def dont_understand(message):
    if 'Погод'.lower() in message.text.lower():
        get_weather(message)
    elif 'https://www.youtube.com/' in message.text:
        get_audio(message)
    elif 'Привет'.lower() in message.text.lower():
        check_reg_users(message)
    elif 'Новост'.lower() in message.text.lower():
        get_news(message)
    elif 'Долл'.lower() in message.text.lower() or 'Евр'.lower() in message.text.lower() or 'Биткои'.lower() in message.text.lower() or 'Курс'.lower() in message.text.lower():
        exchange_rate(message)
    elif 'Обнови город'.lower() in message.text.lower() or 'Измени город'.lower() in message.text.lower():
        update_city(message)
    elif 'Обнови тем'.lower() in message.text.lower() or 'Измени тем'.lower() in message.text.lower():
        update_themes(message)
    else:
        bot.send_message(message.chat.id, 'Моя твоя не понимать!')
        bot.send_message(message.chat.id, f'Знаю команды:\n'
                                          f'/start - Для тех кого я еще не запомнил😑\n'
                                          f'/weather или слово ПОГОДА - Если лень выглядывать в окно😤 и желаешь узнать погоду!☂\n'
                                          f'/news или слово НОВОСТИ  - Если желаешь почитать интересующие тебя темы которые ты мне рассказал'
                                          f' по секрету🤫\n'
                                          f'/rate или слова КУРС,ДОЛЛАР,ЕВРО,БИТКОИН - Если желаешь узнать не уменьшились ли твои накопления😁, ну и заодно курс'
                                          f' валют👀\n'
                                          f'/update_city или ИЗМЕНИ ГОРОД, ОБНОВИ ГОРОД чтобы обновить твой город для актуальности погоды\n'
                                          f'/update_themes или ИЗМЕНИ ТЕМЫ, ОБНОВИ ТЕМЫ чтобы обновить интересующие тебя темы для актуальности новостей\n'
                                          f'-Кинь мне ссылку Youtube, а я тебе верну аудиодорожку!')


if __name__ == '__main__':
    bot.infinity_polling(none_stop=True, timeout=123, skip_pending=True)
