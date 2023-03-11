from bcrypt import kdf
from os import getenv
from sqlalchemy import *
from sqlalchemy.orm import declarative_base as base, sessionmaker, relationship

engine = create_engine("sqlite:///bot.db")
metadata = MetaData()
Base = base(metadata=metadata)
session = sessionmaker(bind=engine)()

kdf_settings = {
	"salt": bytes(getenv("SECRET").encode()),
	"desired_key_bytes": 32,
	"rounds": 100
}

left_chats = Table(
	"left",
	metadata,
	Column("user_id", Integer, ForeignKey("user.id"), nullable=False),
	Column("chat_id", Integer, unique=True, nullable=False)
)


class User(Base):
	__tablename__ = "user"

	id = Column(Integer, primary_key=True)
	telegram_id = Column(Integer, unique=True)

	left_chats = relationship(left_chats)

	username = Column(String(32), nullable=True, unique=True)
	password = Column(String(64), nullable=True)
	status = Column(Integer, CheckConstraint("0 <= status <= 3"))
	team_id = Column(Integer, ForeignKey("team.id"), nullable=True)
	steam_id = Column(String(17), nullable=True, unique=True)

	def set_password(self, password: str):
		self.password = kdf(password=bytes(password), **kdf_settings)

	def check_password(self, password: str):
		return self.password == kdf(password=bytes(password), **kdf_settings)

	def join_team(self, team: "Team"):
		team.add_user(self)
		return self

	def leave_team(self):
		self.team_id = None

	def __repr__(self):
		id = self.id
		username = self.username
		current_team = getattr(self.team, 'name', None)
		return f"<User {user_id=}, {username=}, {current_team=}>"


class Team(Base):
	__tablename__ = "team"

	id = Column(Integer, primary_key=True)
	name = Column(String(64), unique=True)
	users = relationship(User, backref="team")
	owner = Column(Integer, ForeignKey("user.id"), nullable=False, unique=True)

	def add_user(self, user: User):
		if user not in self.users:
			self.users.append(user)
			session.commit()
		return self

	def remove_user(self, user: User):
		if user in self.users:
			self.users.remove(user)
			if user.id == self.owner and len(self.users) > 0:
				self.owner = self.users[-1].id
			session.commit()
		if len(self.users) == 0:
			session.delete(self)
			session.commit()
		return self

	def __repr__(self):
		id = self.id
		name = self.name
		return f"<Team {id=}, {name=}>"


if __name__ == '__main__':
	metadata.create_all(engine)
	session.commit()