import eventlet
eventlet.monkey_patch()
import os
import time
import config
import random
from flask import Flask, request, render_template
from loguru import logger
from telebot import types
from infrastructure import CustomTeleBot, ExtendedMessage
from flask_socketio import SocketIO


app = Flask(__name__)
PROXI_URL = os.getenv('PROXI_URL')
bot = CustomTeleBot(token=config.TOKEN, app=app, proxi_url=PROXI_URL)
sio = SocketIO(app)

@app.route('/')
def index():
	return render_template('index.html')


@sio.on('connect')
def connect():
	logger.info(f'[{request.sid}] has connected')

@sio.on('message')
def handleMessage(msg):
	logger.info(msg)

@bot.message_handler(commands=['start'])
def start(message):
	bot.send_message(chat_id=message.chat.id, aim="to_greet", text="Welcome")

	bot.send_message(chat_id=message.chat.id, aim="get_mood", text="How are you?")
	markup = types.InlineKeyboardMarkup(row_width=2)
	item1 = types.InlineKeyboardButton("Хорошо", callback_data='good')
	item2 = types.InlineKeyboardButton("Не очень", callback_data='bad')

	markup.add(item1, item2)

	bot.send_message(chat_id=message.chat.id, aim="quiz", text='.', reply_markup=markup)


@bot.message_route('get_mood')
def get_mood(message):
	bot.send_message(chat_id=message.chat.id, text="Great")
	markup = types.InlineKeyboardMarkup(row_width=2)
	item1 = types.InlineKeyboardButton("Хорошо", callback_data='good')
	item2 = types.InlineKeyboardButton("Не очень", callback_data='bad')

	markup.add(item1, item2)
	bot.send_message(chat_id=message.chat.id, aim="get_family_mood", text="How is your family?", reply_markup=markup)

@bot.callback_route('get_family_mood')	
def get_family_mood(call):
	bot.send_message(chat_id=call.message.chat.id, text="WAW")

@bot.callback_route('quiz')
def quiz(call):
	if call.data == 'good':
		bot.send_message(chat_id=call.message.chat.id, text="Great")
	else:
		bot.send_message(chat_id=call.message.chat.id, text="Miserable")


if __name__ == "__main__":
	bot.launch()
	sio.run(app, debug=True)
