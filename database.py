from bcrypt import kdf
from os import getenv
from sqlalchemy import *
from sqlalchemy.orm import declarative_base as base, sessionmaker

engine = create_engine("sqlite:///bot.db")
metadata = MetaData()
Base = base(bind=engine, metadata=metadata)
session = sessionmaker(bind=engine, autocommit=True)()

kdf_settings = {
	"salt": bytes(getenv("SECRET")),
	"desired_key_bytes": 32,
	"rounds": 100
}


class User(Base):
	__tablename__ = "user"

	id = Column(Integer, primary_key=True)
	username = Column(String(32), nullable=True, unique=True)
	password = Column(String(64), nullable=True)
	status = Column(Integer, CheckConstraint("0 <= status <= 3"))
	telegram_id = Column(Integer, unique=True)
	team_id = Column(Integer, ForeignKey("team.id"), nullable=True)
	steam_id = Column(Integer(17))

	def set_password(self, password: str):
		self.password = kdf(password=bytes(password), **kdf_settings)

	def check_password(self, password: str):
		return self.password == kdf(password=bytes(password), **kdf_settings)

	def join_team(self, team: "Team"):
		team.add_user(self)
		return self

	def __repr__(self):
		user_id = self.user_id
		username = self.username
		current_team = self.team.name
		return f"<User {user_id=}, {username=}, {current_team=}>"


class Team(Base):
	__tablename__ = "team"

	id = Column(Integer, primary_key=True)
	name = Column(String(64), unique=True)
	users = relationship(User, backref="team")
	owner = Column(Integer, ForeignKey("user.id"), nullable=False, unique=True)

	def add_user(self, user: User):
		self.users.append(user)


if __name__ == '__main__':
	metadata.create_all()