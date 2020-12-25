import six
import json
import copy
import time
from telebot import TeleBot, types
from loguru import logger
from flask import request



class MessageList:
	
	def _get_messages_in_json(self):
		with open('telebot_messages.json', 'r') as f:
			messages_in_json = json.load(f)

		return messages_in_json

	def _put_messages_in_json(self, messages_dict):
		for msg_in_json in messages_dict:
			try:
				msg_in_json.pop('message_list')
			except KeyError:
				pass
		with open('telebot_messages.json', 'w') as f:
			f.write(str(json.dumps(messages_dict, sort_keys=True, indent=4)))

	def _put_message(self, message):
		if message.__class__ != ExtendedMessage:
			raise TypeError('message must be ExtendedMessage type')

		messages = self._get_messages_in_json()
		
		msg_in_json = message.to_json()
		messages.append(msg_in_json)

		self._put_messages_in_json(messages)

	def _get_message_in_json(self, id):
		messages_in_json = self._get_messages_in_json()

		for msg_in_json in messages_in_json:
			if msg_in_json['message_id'] == id:
				return msg_in_json
		else:
			logger.warning("Message hasn't be found")

	def find_message(self, id):
		msg_in_json = self._get_message_in_json(id)

		if msg_in_json:
			ex_message = ExtendedMessage.de_json(msg_in_json)
			ex_message.message_list = self
			return ex_message

	def _set_message_is_answered(self, id, value):
		messages_in_json = self._get_messages_in_json()

		for msg_in_json in messages_in_json:
			if msg_in_json['message_id'] == id:
				msg_in_json['is_answered'] = value
				self._put_messages_in_json(messages_in_json)
				return
		else:
			logger.warning("Message hasn't be found")
			
	def __repr__(self):
		string = "\n"
		for msg in self._get_messages_in_json():
			string += f"<id: {msg.get('message_id')}, aim: {msg.get('aim')}, text: {msg.get('text')}, is_answered: {msg.get('is_answered')}>\n"''
		string += "-" * 30
		return string


class ExtendedMessage(types.Message):
	
	def __init__(self, parent_message, is_answered=False, aim=None):#, *args, **kwargs):
		self.aim = aim
		self._is_answered = is_answered

		for key, value in parent_message.__dict__.items():
			self.__dict__[key] = copy.deepcopy(value)

	@property
	def is_answered(self):
		return self._is_answered
	
	@is_answered.setter
	def is_answered(self, value):
		
		if value.__class__ == bool:
			self.message_list._set_message_is_answered(self.message_id, value)
			self._is_answered = value
		else:
			raise TypeError('is_answered have to be boolean type')

	def get_answered(self):
		self.is_answered = True

	def to_dict(self):
		d = self.__dict__
		d['is_answered'] = self.is_answered
		d.pop('_is_answered')
		return d

	def to_json(self):
		d = {}
		
		for x, y in six.iteritems(self.to_dict()):
			if y == None:
				pass
			elif hasattr(y, '__dict__'):
			    d[x] = y.__dict__
			else:
			    d[x] = y

		return d

	@classmethod
	def de_json(cls, json_dict):
		aim = json_dict.get('aim')
		is_answered = json_dict['is_answered']
		parent_message = types.Message.de_json(json_dict)
		ex_message = ExtendedMessage(parent_message, aim=aim, is_answered=is_answered)
		return ex_message




class CustomTeleBot(TeleBot):
	message_list = MessageList()
	_message_router = {}
	_callback_router = {}
	_involved_functions = [] 

	def __init__(self, app, proxi_url, *args, **kwargs):
		if 'token' in kwargs:
			token = kwargs['token']
		else:
			token = args[0]
		super().__init__(*args, **kwargs)
		
		self.remove_webhook()
		time.sleep(1)
		self.set_webhook(url=f"{proxi_url}/telebot/{token}")

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
					question = self.message_list.find_message(message.reply_to_message.message_id)
					if question:
						message = ExtendedMessage(aim=question.aim, parent_message=message)
					else:
						self.send_message(chat_id=message.chat.id, aim="report_about_uncorrect_using", text="Message you've answered is out of current session")
						return None
				
				# checking whether question is answered	
				if not question.is_answered:
					if message.aim in self._message_router:
						self._message_router[message.aim](message)
						question.get_answered()
					else:
						self.send_message(chat_id=message.chat.id, aim="report_about_uncorrect_using", 
							text="You can't answer this message\nor you have to click on inline button")
				else:
					self.send_message(chat_id=message.chat.id, aim="report_about_uncorrect_using", text="You have already answered this message")

		@self.callback_query_handler(func=lambda call: True)
		def callback_handler(call):
			if call.message.chat.type == "private":
				# transform call.message from Message type to ExtendedMessage type
				question = self.message_list.find_message(call.message.message_id)
				if question:
					call.message = question
				else:
					self.send_message(chat_id=call.message.chat.id, aim="report_about_uncorrect_using", text="Message you've answered is out of current session")
					return None

				
				self._callback_router[call.message.aim](call)
				self.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text,
                reply_markup=None)
				call.message.get_answered()
				self.answer_callback_query(call.id)

	def send_message(self, aim=None, *args, **kwargs):

		message = super().send_message(*args, **kwargs)

		if 'reply_markup' in message.json:
			if not aim:
				raise RuntimeError('if you want to send message with reply markup, you have to enter "aim"')
			if aim not in self._callback_router:
				raise RuntimeError("This aim doesn't have any handler")

		ex_message = ExtendedMessage(aim=aim, parent_message=message)
		self.message_list._put_message(ex_message)
		return ex_message

	def message_route(self, current_aim):
		
		def wrapper(func):

			if current_aim in self._message_router or current_aim in self._callback_router:
				raise RuntimeError('route for this message aim have already existed')

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














	


		




