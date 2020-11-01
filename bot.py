import telebot
import config
import random
from loguru import logger
from telebot import types
from infrastructure import CustomTeleBot, ExtendedMessage

#bot = telebot.TeleBot(config.TOKEN)
bot = CustomTeleBot(config.TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
	bot.send_message(chat_id=message.chat.id, aim="to_greet", text="Welcome")

	bot.send_message(chat_id=message.chat.id, aim="get_mood", text="How are you?")


@bot.message_route('get_mood')
def get_mood(message):
	bot.send_message(chat_id=message.chat.id, text="Great")
	bot.send_message(chat_id=message.chat.id, aim="get_family_mood", text="How is your family?")

@bot.message_route('get_family_mood')	
def get_family_mood(message):
	bot.send_message(chat_id=message.chat.id, text="Cool")



bot.polling(none_stop=True)

