import copy
from telebot import TeleBot, types
from loguru import logger



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

	def __init__(self, parent_message, aim=None, *args, **kwargs):
		self.aim = aim
		self.is_answered = False

		for key, value in parent_message.__dict__.items():
			self.__dict__[key] = copy.deepcopy(value)


class CustomTeleBot(TeleBot):
	message_list = MessageList()
	_message_router = {}

	def polling(self, *args, **kwargs):
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
						answer.is_answered = True
						logger.debug(self.message_list)
					else:
						self.send_message(chat_id=message.chat.id, aim="report_about_uncorrect_using", text="You can't answer this message")
				else:
					self.send_message(chat_id=message.chat.id, aim="report_about_uncorrect_using", text="You have already answered this message")
		
		super().polling(*args, **kwargs)

	def send_message(self, aim=None, *args, **kwargs):
		message = super().send_message(*args, **kwargs)
		ex_message = ExtendedMessage(aim=aim, parent_message=message)
		self.message_list.messages.append(ex_message)
		return ex_message

	def message_route(self, current_aim):
		def wrapper(func):

			if current_aim in self._message_router:
				raise RuntimeError('route for this message aim have already existed')

			for aim in self._message_router:
				if self._message_router[aim].__name__ == func.__name__:
					raise RuntimeError(f'function "{func.__name__}" is used for another message aim')
			else:
				logger.info(f"<aim : {current_aim}, function: {func.__name__}>")
				self._message_router[current_aim] = func

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












	


		




