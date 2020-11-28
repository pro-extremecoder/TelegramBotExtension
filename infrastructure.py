import copy
import time
from telebot import TeleBot, types
from loguru import logger
from flask import request



class MessageList:
	
	def __init__(self, *args):
		self.messages = list(args)

	def __repr__(self):
		string = ""
		for msg in self.messages:
			string += f"<id: {msg.message_id}, aim: {msg.aim}, text: {msg.text}, is_answered: {msg.is_answered}>\n"

		string += "-" * 30
		return string


class ExtendedMessage(types.Message):
	is_answered = False

	def __init__(self, parent_message, aim=None, *args, **kwargs):
		self.aim = aim

		for key, value in parent_message.__dict__.items():
			self.__dict__[key] = copy.deepcopy(value)

	def get_answered(self):
		self.is_answered = True


class CustomTeleBot(TeleBot):
	message_list = MessageList()
	_message_router = {}
	_callback_router = {}
	_involved_functions = [] 

	def __init__(self, app, proxi_url, *args, **kwargs):
		token = kwargs['token']
		super().__init__(*args, **kwargs)
		
		self.remove_webhook()
		time.sleep(1)
		self.set_webhook(url=f"https://{proxi_url}/telebot/{token}")

		@app.route(f'/telebot/{token}', methods=["POST"])
		def webhook():
		    self.process_new_updates([types.Update.de_json(request.stream.read().decode("utf-8"))])
		    return "ok", 200

	def launch(self):
		@self.message_handler(content_types=['text'])
		@self.only_replies
		def text_hanlder(message):
			if message.chat.type == "private":
				# transform message from Message type to ExtendedMessage type
				if message.reply_to_message:
					answers = list(filter(lambda ans: ans.message_id == message.reply_to_message.message_id, self.message_list.messages))
					if answers:
						answer = answers[0]
						message = ExtendedMessage(aim=answer.aim, parent_message=message)
					else:
						self.send_message(chat_id=message.chat.id, aim="report_about_uncorrect_using", text="Message you've answered is out of current session")
						return None
				
				# checking whether answer is answered	
				if not answer.is_answered:
					if message.aim in self._message_router:
						self._message_router[message.aim](message)
						answer.get_answered()
						logger.debug(self.message_list)
					else:
						self.send_message(chat_id=message.chat.id, aim="report_about_uncorrect_using", text="You can't answer this message\nor you have \
to click on inline button")
				else:
					self.send_message(chat_id=message.chat.id, aim="report_about_uncorrect_using", text="You have already answered this message")

		@self.callback_query_handler(func=lambda call: True)
		def callback_handler(call):
			if call.message.chat.type == "private":
				# transform call.message from Message type to ExtendedMessage type
				answers = list(filter(lambda ans: ans.message_id == call.message.message_id, self.message_list.messages))
				if answers:
					call.message = answers[0]
				else:
					self.send_message(chat_id=call.message.chat.id, aim="report_about_uncorrect_using", text="Message you've answered is out of current session")
					return None

				
				self._callback_router[call.message.aim](call)
				self.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text,
                reply_markup=None)
				call.message.get_answered()
				logger.debug(self.message_list)
				self.answer_callback_query(call.id)

	def send_message(self, aim=None, *args, **kwargs):

		message = super().send_message(*args, **kwargs)

		if 'reply_markup' in message.json:
			if not aim:
				raise RuntimeError('if you want to send message with reply markup, you have to enter "aim"')
			if aim not in self._callback_router:
				raise RuntimeError("This aim doesn't have any handler")

		ex_message = ExtendedMessage(aim=aim, parent_message=message)
		self.message_list.messages.append(ex_message)
		return ex_message

	def message_route(self, current_aim):
		
		def wrapper(func):

			if current_aim in self._message_router or current_aim in self._callback_router:
				raise RuntimeError('route for this message aim have already existed')

			'''for aim in self._message_router:
				if self._message_router[aim].__name__ == func.__name__:
					raise RuntimeError(f'function "{func.__name__}" is used for another message aim')'''
			if func.__name__ in self._involved_functions:
				raise RuntimeError(f'function "{func.__name__}" is used for another message aim')
			else:
				logger.info(f"<[MESSAGE_HANDLER]aim : {current_aim}, function: {func.__name__}>")
				self._message_router[current_aim] = func
				self._involved_functions.append(func.__name__)

			return func

		return wrapper 

	def only_replies(self, func):
		
		def wrapper(*args, **kwargs):

			message = args[0]
			if message.reply_to_message:
				return func(*args, **kwargs)
			else:
				self.send_message(chat_id=message.chat.id, aim="unapropriate answer", text="You have to only reply")

		return wrapper

	def callback_route(self, current_aim):

		def wrapper(func):

			if current_aim in self._callback_router or current_aim in self._message_router:
				raise RuntimeError('route for this message aim have already existed')

			if func.__name__ in self._involved_functions:
				raise RuntimeError(f'function "{func.__name__}" is used for another message aim')
			else:
				logger.info(f"<[CALLBACK_HANDLER]aim : {current_aim}, function: {func.__name__}>")
				self._callback_router[current_aim] = func
				self._involved_functions.append(func.__name__)

			return func

		return wrapper 














	


		




