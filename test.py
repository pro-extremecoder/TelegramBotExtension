'''import os
import config
from flask import Flask
from infrastructure import CustomTeleBot

app = Flask(__name__)
bot = CustomTeleBot(app, os.getenv('PROXI_URL'), config.TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
	bot.send_message(aim='greeting', chat_id=message.chat.id, text='HI')

@bot.message_route('greeting')
def greet(message):
	bot.send_message(aim="answer", chat_id=message.chat.id, text='OK')

@bot.message_route('answer')
def answer(message):
	bot.send_message(chat_id=message.chat.id, text='...')


if __name__ == "__main__":
	bot.launch()
	app.run(debug=True)'''

class Celsius:
    def __init__(self, temperature=0):
        self.temperature = temperature

    def to_fahrenheit(self):
        return (self.temperature * 1.8) + 32

    @property
    def temperature(self):
        print("Getting value...")
        return self._temperature

    @temperature.setter
    def temperature(self, value):
        print("Setting value...")
        
        self._temperature = value


# create an object
human = Celsius(37)

print(human.temperature)

print(human.to_fahrenheit())

coldest_thing = Celsius(-300)
