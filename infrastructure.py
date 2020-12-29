import os
import six
import json
import copy
import time
from telebot import TeleBot, types
from loguru import logger
from flask import request



class MessageList:

	'''class that stores all messages sending by bot'''

	def __init__(self):

		'''Constructor that creates telebot_messages.json if necessary'''

		if not os.path.exists('telebot_messages.json'): 
			self._put_messages_in_json([])
	
	def _get_messages_in_json_format(self):

		'''Take all message from telebot_messages.json -> List of Dicts'''

		with open('telebot_messages.json', 'r') as f:
			messages_in_json = json.load(f)

		return messages_in_json

	def _put_messages_in_json(self, messages_dict):

		'''

		Get list of 'messages in json format(dict)' and put in telebot_messages.json 
		
		'''

		for msg_in_json in messages_dict: # remove message_list as it's not JSONDeserializable
			try:
				msg_in_json.pop('message_list')
			except KeyError:
				pass

		with open('telebot_messages.json', 'w') as f:
			f.write(str(json.dumps(messages_dict, sort_keys=True, indent=4)))

	def _put_message(self, message):

		'''Get ExtendedMessage object and append in telebot_messages.json'''

		if message.__class__ != ExtendedMessage:
			raise TypeError('message must be ExtendedMessage type')

		messages = self._get_messages_in_json_format()
		
		msg_in_json = message.to_json()
		messages.append(msg_in_json)

		self._put_messages_in_json(messages)

	def _get_message_in_json_format(self, id):

		'''Return message in json format by id'''
		
		messages_in_json = self._get_messages_in_json_format()

		for msg_in_json in messages_in_json:
			if msg_in_json['message_id'] == id:
				return msg_in_json
		else:
			logger.warning("Message hasn't be found")

	def find_message(self, id):

		'''Find message by id'''

		msg_in_json = self._get_message_in_json_format(id)

		if msg_in_json:
			ex_message = ExtendedMessage.de_json(msg_in_json) # from json format to ExtendedMessage
			ex_message.message_list = self 
			return ex_message

	def _set_message_is_answered(self, id, value):

		'''Set message.is_answered in telebot_message.json'''

		messages_in_json = self._get_messages_in_json_format()

		for msg_in_json in messages_in_json:
			if msg_in_json['message_id'] == id:
				msg_in_json['is_answered'] = value
				self._put_messages_in_json(messages_in_json)
				return
		else:
			logger.warning("Message hasn't be found")

	def _remove_message_reply_markup(self, id):

		'''Remove message reply markup in telebot_message.json'''

		messages_in_json = self._get_messages_in_json_format()

		for msg_in_json in messages_in_json:
			if msg_in_json['message_id'] == id:
				msg_in_json['json'].pop('reply_markup')
				self._put_messages_in_json(messages_in_json)
				return
		else:
			logger.warning("Message hasn't be found")

	def _clear(self):

		'''Clear MessageList'''

		self._put_messages_in_json([])
		logger.critical('MESSAGE LIST HAS BEEN CLEARED')
			
	def __repr__(self):

		'''Return a string of base information about message in MessageList'''

		string = "\n"
		pattern = "<id: {}, aim: {}, text: {}, is_answered: {}>\n"
		for msg in self._get_messages_in_json_format():
			args = [msg.get('message_id'), msg.get('aim'), msg.get('text'), msg.get('is_answered')]
			string += pattern.format(*args)
		string += "-" * 30

		return string


class ExtendedMessage(types.Message):

	'''class that extends base Message class'''
	
	def __init__(self, parent_message, is_answered=False, aim=None):

		'''__init__(self, parent_message, is_answered=False, aim=None)'''

		self.aim = aim # aim for message or callback routing
		self._is_answered = is_answered


		for key, value in parent_message.__dict__.items(): # coping attributes of parent base message 
			self.__dict__[key] = copy.deepcopy(value)


	@property
	def is_answered(self):
		return self._is_answered
	
	@is_answered.setter
	def is_answered(self, value):
		
		if value.__class__ == bool:
			self.message_list._set_message_is_answered(self.message_id, value) # recording changes in telebot_message.json
			self._is_answered = value
			self.json['is_answered'] = value
		else:
			raise TypeError('is_answered has to be boolean type')

	def get_answered(self):

		'''set message.is_answered to True value'''

		self.is_answered = True

	def remove_reply_markup(self):

		'''Remove reply markup'''

		try:
			if self.json['reply_markup']:
				self.message_list._remove_message_reply_markup(self.message_id) # record changes in telebot_message.json
		except AttributeError:
			logger.warning('this message does not have reply markup')
		

	def to_dict(self):

		'''Own method instead of __dict__ method'''

		d = self.__dict__
		d['is_answered'] = self.is_answered
		d.pop('_is_answered')
		return d

	def to_json(self):

		'''Convert ExtendedMessage to json format'''

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

		'''Convert json format to ExtendedMessage'''
		
		aim = json_dict.get('aim')
		is_answered = json_dict['is_answered']

		json_dict = json_dict['json'] 
		json_dict['aim'] = aim
		json_dict['is_answered'] = is_answered	

		parent_message = types.Message.de_json(json_dict)
		ex_message = ExtendedMessage(parent_message, aim=aim, is_answered=is_answered)
		ex_message.json = json_dict

		return ex_message




class CustomTeleBot(TeleBot):

	'''class that extends base TeleBot class'''

	message_list = MessageList()
	_message_router = {} # dict for message routing {aim : function}
	_callback_router = {} # dict for callback routing {aim : function}
	_involved_functions = [] # all message and callback handlers

	def __init__(self, app, proxi_url, *args, **kwargs):

		'''__init__(self, app, proxi_url, *args, **kwargs)'''

		if 'token' in kwargs:
			token = kwargs['token']
		else:
			token = args[0]

		super().__init__(*args, **kwargs)
		
		# setting webhook
		self.remove_webhook()
		time.sleep(1)
		self.set_webhook(url=f"{proxi_url}/telebot/{token}")

		# setting redirectng to self.message_handler or self.callback_query_handler
		@app.route(f'/telebot/{token}', methods=["POST"])
		def webhook():
		    self.process_new_updates([types.Update.de_json(request.stream.read().decode("utf-8"))])
		    return "ok", 200

	def launch(self):

		'''Function that run base message handler and callback query handler'''

		@self.message_handler(content_types=['text'])
		@self.only_replies
		def text_hanlder(message):

			'''Base text message handler'''

			if message.chat.type == "private":
				# transforming message from Message type to ExtendedMessage type
				question = self.message_list.find_message(message.reply_to_message.message_id) # finding message which has been replied
				if question:
					message = ExtendedMessage(aim=question.aim, parent_message=message)
				else:
					self.send_message(chat_id=message.chat.id, aim="report_about_uncorrect_using", 
						text="Message you've answered is out of current session")

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
					self.send_message(chat_id=message.chat.id, aim="report_about_uncorrect_using", 
						text="You have already answered this message")

		@self.callback_query_handler(func=lambda call: True)
		def callback_handler(call):

			'''Base callback query handler'''

			if call.message.chat.type == "private":
				# transforming call.message from Message type to ExtendedMessage type
				question = self.message_list.find_message(call.message.message_id) # finding message which has been replied(with reply markup)
				if question:
					call.message = question
				else:
					self.send_message(chat_id=call.message.chat.id, aim="report_about_uncorrect_using", 
						text="Message you've answered is out of current session")

					return None

				
				self._callback_router[call.message.aim](call)
				self.__edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, 
					text=call.message.text, reply_markup=None) # removing reply markup in chat

				call.message.remove_reply_markup() # removing reply markup in json
				call.message.get_answered()
				self.answer_callback_query(call.id)

	def send_message(self, aim=None, *args, **kwargs):

		'''Extended send_message method with aim arguement'''

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

		'''Message route decorator that gets aim as arguement'''
		
		def wrapper(func):

			if current_aim in self._message_router or current_aim in self._callback_router: # checking wheather aim is unique
				raise RuntimeError('route for this message aim have already existed')

			if func.__name__ in self._involved_functions: # checking wheather function is unique
				raise RuntimeError(f'function "{func.__name__}" is used for another message aim')
			else:
				logger.info(f"<[MESSAGE_HANDLER]aim : {current_aim}, function: {func.__name__}>")
				self._message_router[current_aim] = func
				self._involved_functions.append(func.__name__)

			return func

		return wrapper 

	def only_replies(self, func):

		'''Decorator that allows only messages which are replied'''
		
		def wrapper(*args, **kwargs):

			message = args[0]
			if message.reply_to_message:
				return func(*args, **kwargs)
			else:
				self.send_message(chat_id=message.chat.id, aim="unapropriate answer", text="You have to only reply")

		return wrapper

	def callback_route(self, current_aim):

		'''Callback route decorator that gets aim as arguement'''

		def wrapper(func):

			if current_aim in self._callback_router or current_aim in self._message_router: # checking wheather aim is unique
				raise RuntimeError('route for this message aim have already existed')

			if func.__name__ in self._involved_functions: # checking wheather function is unique
				raise RuntimeError(f'function "{func.__name__}" is used for another message aim')
			else:
				logger.info(f"<[CALLBACK_HANDLER]aim : {current_aim}, function: {func.__name__}>")
				self._callback_router[current_aim] = func
				self._involved_functions.append(func.__name__)

			return func

		return wrapper 

	def edit_message_text(self, *args, **kwargs):
		raise AttributeError("'CustomTeleBot' object has no attribute 'edit_message_text'")

	def __edit_message_text(self, *args, **kwargs):
		super().edit_message_text(*args, **kwargs)














	


		




