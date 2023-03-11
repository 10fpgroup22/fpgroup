from bcrypt import kdf
from sqlalchemy import *
from sqlalchemy.orm import declarative_base as base

engine = create_engine("sqlite:///bot.db")
metadata = MetaData()
Base = base(bind=engine, metadata=metadata)


class User(Base):
	__tablename__ = "user"

	user_id = Column(Integer, primary_key=True)
	username = Column(String(32), nullable=True, unique=True)
	password = Column(String(64), nullable=True)
	telegram_id = Column(Integer, unique=True)
	steam_id = Column(Integer(17))

	def set_password(self, password: str):
		self.password = kdf(password=bytes(password), **kdf_settings)

	def check_password(self, password: str):
		return self.password == kdf(password=bytes(password), **kdf_settings)

	def __repr__(self):
		user_id = self.user_id
		username = self.username
		return f"<User {user_id=}, {username=}>"
