# from aiohttp.web import middleware
from bcrypt import kdf
from datetime import datetime, timedelta
from jwt import encode, decode, exceptions
from os import getenv
from sqlalchemy import *
from sqlalchemy.orm import declarative_base as base, sessionmaker, relationship
from typing import Union, Any

__all__ = ["Team", "User", "Chat", "session", "update_status"]

engine = create_engine("sqlite:///bot.db")
metadata = MetaData()
Base = base(metadata=metadata)
session = sessionmaker(bind=engine)()

kdf_settings = {
	"salt": bytes(getenv("SECRET", "").encode()),
	"desired_key_bytes": 32,
	"rounds": 100
}


class FieldMixin(object):
	@classmethod
	def from_field(cls, field: Union[str, Column], value: Any):
		return session.query(cls).filter(getattr(cls, field, field) == value).all()


class ChatTagging(Base):
	__tablename__ = "chat_tags"

	user_id = Column(None, ForeignKey('user.id'), primary_key=True)
	chat_id = Column(None, ForeignKey('chat.id'), primary_key=True)
	left = Column(Boolean, default=False)

	user = relationship('User', viewonly=True)
	chat = relationship('Chat', viewonly=True)


class Team(Base, FieldMixin):
	__tablename__ = "team"

	id = Column(Integer, primary_key=True)
	name = Column(String(64), unique=True)
	captain = Column(ForeignKey('user.id'), nullable=False)

	def add_user(self, user: "User"):
		if user not in self.teammates:
			self.teammates.append(user)
			session.commit()
		return self

	def remove_user(self, user: "User"):
		if user in self.teammates:
			if user.id == self.captain and len(self.teammates) > 0:
				self.captain = self.teammates[-1].id
			self.teammates.remove(user)
		if len(self.teammates) == 0:
			session.delete(self)
		session.commit()
		return self

	def promote(self, user: "User", promoter: "User"):
		if self.captain == promoter.id:
			self.captain = user.id
			session.commit()
			return True
		return False

	@classmethod
	def search(cls, name: str):
		return session.query(cls).filter(cls.name.like(f"%{name}%")).all()

	def __repr__(self):
		id = self.id
		name = self.name
		return f"<Team {id=}, {name=}>"


class Chat(Base, FieldMixin):
	__tablename__ = "chat"

	id = Column(Integer, primary_key=True)
	telegram_id = Column(Integer, unique=True, nullable=False)

	def get_tags(self):
		return list(map(lambda user: user.telegram, self.left))

	@classmethod
	def from_telegram(cls, telegram_id: int):
		chat = cls.from_field('telegram_id', telegram_id)
		if len(chat) == 0:
			chat = cls(telegram_id=telegram_id)
			session.add(chat)
			session.commit()
		else:
			chat = chat[0]
		return chat

	def __contains__(self, user):
		return user in self.left

	def __repr__(self):
		id = self.id
		telegram_id = self.telegram_id
		return f"<Chat {id=}, {telegram_id}>"


class User(Base, FieldMixin):
	__tablename__ = "user"
	__table_args__ = (
		CheckConstraint("(username IS NOT NULL AND password IS NOT NULL) OR telegram IS NOT NULL"),
	)

	REASONS = {False: {9: 'you must leave team at first', 1: 'team with this name already exists'}, True: 'team created succesfully'}

	id = Column(Integer, primary_key=True)
	username = Column(String(32), unique=True)
	password = Column(String(64))
	telegram = Column(Integer, unique=True)
	status = Column(Integer, CheckConstraint("0 <= status <= 3"), default=0)
	team_id = Column(ForeignKey('team.id'), nullable=True)

	team = relationship(Team, foreign_keys=[team_id], backref="teammates")
	left_tags = relationship(Chat, secondary="chat_tags", primaryjoin="and_(chat_tags.c.chat_id == Chat.id, chat_tags.c.left == True)", backref="left", lazy='dynamic')

	def set_password(self, password: str):
		self.password = kdf(password=bytes(password.encode()), **kdf_settings)
		return True

	def check_password(self, password: str):
		return self.password == kdf(password=bytes(password.encode()), **kdf_settings)

	def join_team(self, team: "Team"):
		if self.team_id == None:
			self.team_id = team.id
			session.commit()
		return self

	def leave_team(self):
		if self.team_id != None:
			self.team_id = None
			session.commit()
		return self

	def create_team(self, name: str):
		if self.team_id != None:
			return False, 0
		elif len(Team.search(name)) > 0:
			return False, 1
		team = Team(name=name, captain=self.id)
		session.add(team)
		session.commit()
		self.team_id = team.id
		session.commit()
		return True,

	def leave_chat_tag(self, chat: Union[Chat, int]):
		if isinstance(chat, Chat) and chat not in self.left_tags:
			self.left_tags.append(chat)
			session.commit()
			return True
		elif isinstance(chat, int):
			return self.leave_chat_tag(Chat.from_telegram(chat))
		return False

	def add_chat_tag(self, chat: Union[Chat, int]):
		if chat in self.left_tags:
			self.left_tags.remove(chat)
			session.commit()
			return True
		elif isinstance(chat, int):
			return self.add_chat_tag(Chat.from_telegram(chat))
		return False

	@classmethod
	def from_telegram(cls, telegram_id: int):
		user = cls.from_field('telegram_id', telegram_id)
		if len(user) == 0:
			user = cls(telegram_id=telegram_id)
			session.add(user)
			session.commit()
		else:
			user = user.first()
		return user

	@property
	def token(self):
		return encode({"id": self.id, "username": self.username, "exp": datetime.utcnow() + _month}, kdf_settings["salt"], algorithm="HS256")

	@classmethod
	def from_token(cls, token: str = '', refresh: bool = False):
		try:
			payload = decode(token, kdf_settings["salt"], leeway=timedelta(days=1), algorithms=["HS256"])
		except exceptions.ExpiredSignatureError:
			if not refresh:
				return False
		except:
			return False
		user = cls.from_field('username', payload['username'])
		if len(user) == 0:
			return False
		return user[0]

	@classmethod
	def from_username(cls, username: str | None = None, password: str | None = None, **kwargs):
		username = username or kwargs.pop('username', '')
		password = password or kwargs.pop('password', '')
		assert len(username) > 0 and len(password) >= 0
		user = cls.from_field('username', username)
		if len(user) == 0:
			user = cls(username=username)
			user.set_password(password)
			session.add(user)
			session.commit()
			return user
		else:
			user = user[0]
			if user.check_password(password):
				return user

	def __repr__(self):
		id = self.id
		current_team = getattr(self.team, 'name', None)
		return f"<User {id=}, {current_team=}>"


def update_status(admins: list[int]):
	session.query(User).filter(User.status==3).update({User.status: 0})
	for admin_id in admins:
		admin = User.from_telegram(admin_id)
		admin.status = 3
	session.commit()


# @middleware
# async def auth_middleware(request, handler):
# 	request.user = User.from_token(request.session)
# 	if not request.user:
# 		request.session = ''
# 	return await handler(request)


if __name__ == '__main__':
	metadata.create_all(engine)