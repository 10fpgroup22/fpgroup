from sqlalchemy import create_engine, MetaData, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

db = create_engine("sqlite:///app.db")
metadata = MetaData()
Base = declarative_base(metadata=metadata)
Session = sessionmaker(bind=db)
session = Session()


class Team(Base):
	__tablename__ = "team"

	id = Column(Integer, primary_key=True, autoincrement=True)
	name = Column(String(64), unique=True)
	max_teammates = Column(Integer, )
	teammates = relationship("User")

	def add_teammate(self, user: "User"):
		pass

	def __repr__(self):
		name = self.name
		return f"<Team({name=})>"


class User(Base):
	__tablename__ = "user"

	id = Column(Integer, primary_key=True, autoincrement=True)
	steam_id = Column(String(20), unique=True)
	telegram = Column(Integer, unique=True)
	team_id = Column(Integer, ForeignKey("team.id"), nullable=True)

	def create_team(self, name=):
		pass

	def __repr__(self):
		steam_id = self.steam_id
		telegram = self.telegram
		team_id = self.team_id
		return f"<User({steam_id=}, {telegram=}, {team_id=})>"


metadata.create_all(db)
