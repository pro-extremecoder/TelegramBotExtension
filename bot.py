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



bot.polling(none_stop=True)