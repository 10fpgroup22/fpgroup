from bcrypt import kdf
from os import getenv
from sqlalchemy import *
from sqlalchemy.orm import declarative_base as base, sessionmaker, relationship
from typing import Union

engine = create_engine("sqlite:///bot.db")
metadata = MetaData()
Base = base(metadata=metadata)
session = sessionmaker(bind=engine)()

kdf_settings = {
	"salt": bytes(getenv("SECRET", "").encode()),
	"desired_key_bytes": 32,
	"rounds": 100
}


left_tags = Table(
	"left", metadata,
	Column("user_id", Integer, ForeignKey("user.id"), primary_key=True),
	Column("chat_id", Integer, ForeignKey("chat.id"), primary_key=True)
)

class Team(Base):
	__tablename__ = "team"

	id = Column(Integer, primary_key=True)
	name = Column(String(64), unique=True)
	owner = Column(Integer, ForeignKey("user.id"), nullable=False, unique=True)

	def add_user(self, user: "User"):
		if user not in self.members:
			self.members.append(user)
			session.commit()
		return self

	def remove_user(self, user: "User"):
		if user in self.members:
			self.members.remove(user)
			if user.id == self.owner and len(self.members) > 0:
				self.owner = self.members[-1].id
		if len(self.members) == 0:
			session.delete(self)
		session.commit()
		return self

	def promote(self, user: "User", admin: "User"):
		if self.owner == owner.id:
			self.owner = user.id
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


class Chat(Base):
	__tablename__ = "chat"

	id = Column(Integer, primary_key=True)
	telegram_id = Column(Integer, unique=True, nullable=False)

	def get_tags(self):
		return list(map(lambda user: user.telegram_id, self.left))

	@classmethod
	def from_telegram_id(cls, telegram_id: int):
		obj = session.query(cls).filter(cls.telegram_id == telegram_id).all()
		if len(obj) == 0:
			obj = cls(telegram_id=telegram_id)
			session.add(obj)
			session.commit()
		else:
			obj = obj[0]
		return obj

	def __contains__(self, item):
		return item in self.left

	def __repr__(self):
		id = self.id
		telegram_id = self.telegram_id
		return f"<Chat {id=}, {telegram_id}>"


class User(Base):
	__tablename__ = "user"

	id = Column(Integer, primary_key=True)
	telegram_id = Column(Integer, unique=True)
	left_tags = relationship(Chat, secondary=left_tags, primaryjoin="and_(Chat.id==left.c.chat_id, User.id==left.c.user_id)",
							 foreign_keys=[left_tags.c.chat_id, left_tags.c.user_id], backref="left")
	username = Column(String(32), nullable=True, unique=True)
	password = Column(String(64), nullable=True)
	status = Column(Integer, CheckConstraint("0 <= status <= 3"))
	team_id = Column(Integer, ForeignKey("team.id"), nullable=True)
	steam_id = Column(String(17), nullable=True, unique=True)

	team = relationship(Team, foreign_keys=[team_id], backref="members")

	def set_password(self, password: str):
		self.password = kdf(password=bytes(password), **kdf_settings)

	def check_password(self, password: str):
		return self.password == kdf(password=bytes(password), **kdf_settings)

	def join_team(self, team: "Team"):
		team.add_user(self)
		return self

	def leave_team(self):
		self.team_id = None
		session.commit()

	def create_team(self, name: str):
		if self.team_id != None:
			return False
		team = Team(name=name, owner=self.id)
		session.add(team)
		session.commit()
		self.team_id = team.id
		session.commit()
		return True

	def left_chat_tag(self, chat: Union[Chat, int]):
		if isinstance(chat, Chat) and chat not in self.left_tags:
			self.left_tags.append(chat)
			session.commit()
			return True
		elif isinstance(chat, int):
			_chat = session.query(Chat).filter(Chat.telegram_id == chat).all()
			if len(_chat) == 0:
				_chat = Chat(telegram_id=chat)
				session.add(_chat)
				session.commit()
			else:
				_chat = _chat[0]
			return self.left_chat_tag(_chat)
		return False

	def add_chat_tag(self, chat: Union[Chat, int]):
		if chat in self.left_tags:
			self.left_tags.remove(chat)
			session.commit()
			return True
		elif isinstance(chat, int):
			return self.add_chat_tag(Chat.from_telegram_id(chat))
		return False

	@classmethod
	def from_telegram_id(cls, telegram_id: int):
		obj = session.query(cls).filter(cls.telegram_id == telegram_id).all()
		if len(obj) == 0:
			obj = cls(telegram_id=telegram_id)
			session.add(obj)
			session.commit()
		else:
			obj = obj[0]
		return obj

	def __repr__(self):
		id = self.id
		username = self.username
		current_team = getattr(self.team, 'name', None)
		return f"<User {id=}, {username=}, {current_team=}>"


if __name__ == '__main__':
	# metadata.create_all(engine)
	# session.commit()

	chat = session.query(Chat).filter(Chat.id==1).all()
	print(chat[0].left)
