import random
from minilib import Loader, Dispatcher


class Card(Loader):
	RANKS = {0: 'A', 1: '2', 2: '3', 3: '4', 4: '5', 5: '6', 6: '7', 7: '8', 8: '9', 9: '10', 10: 'J', 11: 'Q', 12: 'K', 13: 'A'}
	SUITS = {0: '♦', 1: '♣', 2: '♥', 3: '♠'}
	__fields__ = {"rank": "rank", "suit": "suit"}

	def __init__(self, rank: int = 1, suit: int = 0):
		assert rank in self.RANKS and rank > 0, "Invalid card rank"
		assert suit in self.SUITS, "Invalid card suit"
		self._value = (rank << 2) + suit

	@property
	def rank(self):
		return self._value >> 2

	@rank.setter
	def rank(self, rank):
		if isinstance(rank, str) and rank in self.RANKS.values():
			rank = [k for k, v in self.RANKS.items() if rank == v][0]
		if isinstance(rank, int) and rank in self.RANKS:
			self._value = (rank << 2) + self.suit

	@property
	def suit(self):
		return self._value & 3

	@suit.setter
	def suit(self, suit):
		if isinstance(rank, str) and rank in self.SUITS.values():
			suit = [k for k, v in self.SUITS.items() if suit == v][0]
		if isinstance(suit, int) and suit in self.SUITS:
			self._value = (self.rank << 2) + suit

	def __hash__(self):
		return int(self)

	def __lt__(self, other: "Card"):
		return int(self) < int(other)

	def __int__(self):
		return self._value

	def __str__(self):
		return f"{self.RANKS[self.rank]}{self.SUITS[self.suit]}"

	def __format__(self, spec: str):
		if spec in ["r", "rank"]:
			return self.RANKS[self.rank]
		elif spec in ["s", "suit"]:
			return self.SUITS[self.suit]
		elif spec in ["rs", "rsuit", "ranks", "ranksuit"]:
			return str(self)

		return str(self)

	def __repr__(self):
		return str(self)


class Cards(Loader):
	__field__ = {"cards": "_cards", "cards_count": "_cards_count"}

	def __init__(self, *, cards_count: int = 36):
		assert cards_count in [36, 52], "Count of cards must be 36 or 52"
		self._cards_count = cards_count
		self._cards: list[Card] = []
		self._counter = random.randint(0, 10240)

	def shuffle(self):
		for rank in list(Card.RANKS.keys())[-(self._cards_count // 4):]:
			for suit in Card.SUITS:
				card = Card(rank, suit)
				if card not in self._cards:
					self._cards.append(card)
					continue
				del card
		random.seed(self._counter)
		random.shuffle(self._cards)

		return self

	def add(self, card: Card):
		if card not in self._cards:
			self._cards.append(card)
		return True

	def pop(self):
		return self._cards.pop()

	def __len__(self):
		return len(self._cards)

	def __str__(self):
		return ','.join(self._cards)

	def __contains__(self, card: Card):
		if isinstance(card, Card):
			return card in self._cards
		return False

	def __format__(self):
		return repr(self)

	def __repr__(self):
		return f'<Cards {len(self)}/{self._cards_count}>'


class Player(Loader):
	__fields__ = {"user_id": "_user_id", "username": "username", "cards": "cards", "combination": "combination"}

	def __init__(self, user_id: int, username: str | None = None):
		self._user_id = user_id
		self.username = username
		self._cards = []
		self.combination = tuple()

	@property
	def cards(self):
		return self._cards

	@cards.setter
	def cards(self, cards: list[Card]):
		self._cards = sorted(set(cards), key=lambda c: (c.rank, c.suit))

	def reset(self):
		self._cards = []
		self.combination = tuple()

	def __len__(self):
		return len(self._cards)

	def __getitem__(self, index: int):
		return self.combination[index]

	def __int__(self):
		return self._user_id

	def __str__(self):
		if len(self._cards) > 0 and self.combination:
			return CombinationManager.from_combination(self.combination)
		return repr(self)

	def __format__(self):
		return str(self)

	def __repr__(self):
		ret = f'<Player id={self._user_id}'
		if self.username:
			return ret + f', username={self.username}>'
		else:
			return ret + '>'


class CombinationManager(Loader):
	COMBINATIONS = {
		0: '{0:r} is highest card',
		1: 'Pair on {0:r}',
		2: 'Two pairs on {0:r} and {1:r}',
		3: 'Three of a kind on {0:r}',
		4: 'Straight to {0:r}',
		5: 'Flush with highest card {0:r}',
		6: 'Full house on {0:r} and {1:r}',
		7: 'Four of a kind on {0:r}',
		8: 'Straight flush to {0:r}',
		9: 'Royale Straight flush'
	}

	__fields__ = {"table_cards": "table_cards"}

	def __init__(self, table_cards: list[Card] | None = None):
		self._table_cards = table_cards or []

	@property
	def table_cards(self):
		return self._table_cards

	@table_cards.setter
	def table_cards(self, table_cards: list[Card]):
		self._table_cards = list(set(table_cards))

	@staticmethod
	def _count(cards: list[Card], count: int = 2):
		ret = {}
		for card in cards:
			c = ret.setdefault(card.rank, [])
			c.append(card)
		return [x[0] for x in ret.values() if len(x) == count]

	@staticmethod
	def pairs(cards: list[Card]):
		c = CombinationManager._count(cards)
		if len(c) == 1:
			return 1, c
		elif len(c) >= 2:
			return 2, c[-2:]
		del c

	@staticmethod
	def three_of_kind(cards: list[Card]):
		c = CombinationManager._count(cards, 3)
		if len(c) > 0:
			return 3, c[-1:]
		del c

	@staticmethod
	def straight(cards: list[Card]):
		straight = {c.rank: c for c in cards}
		ret = []
		ranks = sorted(straight.keys())
		for x in range(len(ranks) - 4):
			if ranks[x + 4] - 4 == ranks[x]:
				ret = [v for k, v in straight.items() if ranks[x] <= k <= ranks[x + 4]]
			elif ranks[x] == 1 and ranks[x + 3] == 4 and ranks[-1] == 13:
				ret = [v for k, v in straight.items() if 0 <= k <= 4]
				ret.insert(0, straight[13])

		del straight, ranks

		if ret:
			return 4, ret[::-1]

	@staticmethod
	def flush(cards: list[Card]):
		r = {}
		for card in reversed(cards):
			suit = r.setdefault(card.suit, [])
			suit.append(card)
			if len(suit) == 5:
				return 5, sorted(suit, key=lambda c: c.rank, reverse=True)
		del r

	@staticmethod
	def full_house(cards: list[Card]):
		p = CombinationManager.pairs(cards)
		if p and len(p) > 0:
			t = CombinationManager.three_of_kind(cards)
			if t and len(t) > 0:
				return 6, [p[1][-1], t[1][-1]]
			del t
		del p

	@staticmethod
	def four_of_kind(cards: list[Card]):
		c = CombinationManager._count(cards, 4)
		if len(c) > 0:
			return 7, c[-1:]
		del c

	@staticmethod
	def straight_flush(cards: list[Card]):
		s = CombinationManager.straight(cards)
		if s:
			f = CombinationManager.flush(s[1])
			if f:
				return (8, s[1]) if s[1][0].rank != 13 else (9, s[1])
			del f
		del s

	def resolve_combination(self, cards: list[Card], as_string: bool = False):
		cards = sorted(set(cards + self._table_cards), key=lambda card: int(card))
		combination = []

		for combo_fn in [self.straight_flush, self.four_of_kind,
						 self.full_house, self.flush, self.straight,
						 self.three_of_kind, self.pairs]:
			combination = combo_fn(cards)
			if combination:
				break
			else:
				combination = 0, [cards[-1]]
		if as_string:
			return self.from_combination(combination)
		else:
			return combination

	@staticmethod
	def from_combination(combination: tuple[int, list[Card]]):
		return CombinationManager.COMBINATIONS[combination[0]].format(*combination[1])

	def compare(self, player1: Player, player2: Player):
		if player1[0] == player2[0]:
			for c1, c2 in zip(player1[1], player2[1]):
				if c1 < c2:
					return player2
				elif c1 > c2:
					return player1
			for c1, c2 in zip(player1.cards, player2.cards):
				if c1 < c2:
					return player2
				elif c1 > c2:
					return player1
		elif player1[0] < player2[0]:
			return player2
		else:
			return player1


class PokerManager(Dispatcher, Loader):
	__fields__ = {"players": "_players", "combination_manager": "_combination_manager", "paused": "_pause", "started": "_start", "deck": "_deck", "decks": "_decks"}

	_combination_manager = CombinationManager()

	def __init__(self, players: list[dict[int, str]]):
		assert 2 <= len(players) <= 9
		super().__init__()
		self.start = self.dispatcher(self.start)
		self._players = [Player(id, name) if name else Player(id) for plrs in players for id, name in plrs.items()]
		self._decks = [Cards(cards_count=52), Cards(cards_count=52), Cards(cards_count=52)]
		self._pause = False
		self._start = False

	@property
	def started(self):
		return self._start

	@property
	def players(self):
		return self._players

	@property
	def table_cards(self):
		return self._combination_manager.table_cards

	@table_cards.setter
	def table_cards(self, cards: list[Card]):
		self._combination_manager.table_cards = cards

	def start(self):
		assert not self._start, "Game already started"
		self._deck = self._decks.pop(0)
		self._deck.shuffle()
		self._start = True
		self._pause = False

	def toggle(self):
		assert self._start, "Game must be started"
		self._pause = not self._pause

	def stop(self):
		assert self._start, "Game can be stopped only if it is started"
		self._decks.append(self._deck)
		self._deck = None
		self._start = False
		self._pause = False

	def player_gift(self):
		raise NotImplemented

	def table_gift(self):
		raise NotImplemented

	def __len__(self):
		return len(self._players)

	def __repr__(self):
		return f'<{self.__class__.__name__} players={len(self)}, started={self._start}, paused={self._pause}>'


class Holdem(PokerManager):
	def player_gift(self):
		assert self._start and not self._pause and len(self.table_cards) == 0, "Game is not started or paused"
		for _ in range(2):
			for player in self.players:
				if len(player) == 2:
					break
				elif len(player) > 2:
					raise
				player.cards = player.cards + [self._deck.pop()]
				player.combination = self._combination_manager.resolve_combination(player.cards)
			self._deck.add(self._deck.pop())
		return self._players

	def table_gift(self, gift: int = 0):
		assert self._start and not self._pause, "Game is not started or paused"
		if 0 < gift < 4 and len(self.table_cards) < 5:
			if gift == 1 and len(self.table_cards) == 0:
				for _ in range(3):
					self.table_cards.append(self._deck.pop())
			elif gift in [2, 3] and len(self.table_cards) >= 3:
				self.table_cards.append(self._deck.pop())
			self._deck.add(self._deck.pop())
		for player in self.players:
			player.combination = self._combination_manager.resolve_combination(player.cards)
		return self.table_cards

	def get_winner(self):
		assert self._start and not self._pause, "Game is not started or paused"
		if len(self.table_cards) == 5:
			winner = self.players[0]
			for player in self.players[1:]:
				w = self._combination_manager.compare(winner, player)
				if not w:
					random.seed(self._dec)
					w = random.choice([winner, player])
				winner = w
			return winner
