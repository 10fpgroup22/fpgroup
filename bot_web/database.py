from sqlalchemy import create_engine, MetaData, Column, Integer, String, ForeignKey, CheckConstraint
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

db = create_engine("sqlite:///app.db")
metadata = MetaData()
Base = declarative_base(metadata=metadata)
Session = sessionmaker(bind=db)
session = Session()


class Actions:
	TEAM_ADD: int = 1
	TEAM_REMOVE: int = 2


class Team(Base):
	__tablename__ = "team"

	id = Column(Integer, primary_key=True, autoincrement=True)
	name = Column(String(64), unique=True)
	captain = Column(Integer, ForeignKey('user.id'), nullable=False, unique=True)
	max_teammates = Column(Integer, CheckConstraint("max_teammates in [3, 6]"), default=6)
	teammates = relationship("User")

	def teammate(self, user: "User", *, action: int = Actions.TEAM_ADD):
		if user.team_id == None:
			user.team_id = self.team_id
		elif user.team_id == self.id and action == Actions.TEAM_REMOVE:
			user.team_id = None

		if session.dirty:
			session.commit()

	def edit(self, **kwargs):
		kwargs.setdefault('name', self.name)
		kwargs.setdefault('max_teammates', self.max_teammates)
		captain = kwargs.setdefault('captain', self.captain)
		assert captain in self.teammates
		kwargs.pop('teammates', None)
		for attr, value in kwargs.items():
			if hasattr(self, attr):
				setattr(self, attr, value)
		session.commit()

	def __repr__(self):
		name = self.name
		return f"<Team({name=})>"


class User(Base):
	__tablename__ = "user"

	id = Column(Integer, primary_key=True, autoincrement=True)
	telegram = Column(Integer, unique=True)
	steam_id = Column(String(20), unique=True)
	team_id = Column(Integer, ForeignKey("team.id"), nullable=True)

	def create_team(self, name: str, max_teammates: int = 6):
		team = Team(name=name, max_teammates=max_teammates, captain=self.id)
		session.add(team)
		self.team_id = team.id
		session.commit()

	def edit(self, **kwargs):
		kwargs.setdefault('telegram', self.telegram)
		kwargs.setdefault('team_id', self.team_id)
		kwargs.setdefault('steam_id', self.steam_id)
		for attr, value in kwargs.items():
			if hasattr(self, attr):
				setattr(self, attr, value)
		session.commit()

	def __repr__(self):
		steam_id = self.steam_id
		telegram = self.telegram
		team_id = self.team_id
		return f"<User({telegram=}, {steam_id=}, {team_id=})>"


metadata.create_all(db)
