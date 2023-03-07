import asyncio
import atexit
import inspect
import logging
import re

from concurrent.futures import Future, as_completed
from json import loads
from queue import Queue
from threading import Thread
from typing import Any, Optional, Union, Iterable, Coroutine, Callable

__all__ = ["Dispatcher", "Executor", "Loader", "Function", "logger", "infinite", "init", "build", "get_pattern", "run"]

Function = Union[Callable, Coroutine]

logger = logging.Logger('minilib.logger')
c = logging.StreamHandler()
c.setFormatter(logging.Formatter(
	fmt="[%(asctime)s %(filename)s:%(lineno)s %(levelname)s] %(message)s",
	datefmt="%H:%M:%S %d.%m.%y"
))
logger.addHandler(c)


class StopInfinite(Exception):
	pass


class Executor:
	class _Item(Future):
		def __init__(self, func, args, kwargs):
			super().__init__()
			self.func = func
			self.args = args
			self.kwargs = kwargs

		def result(self, timeout: float = 5.0):
			try:
				return super().result(timeout=timeout)
			except TimeoutError as e:
				return self

		def run(self, loop: asyncio.AbstractEventLoop):
			try:
				result = self.func(*self.args, **self.kwargs)
				if inspect.iscoroutinefunction(self.func):
					result = loop.run_until_complete(result)
			except StopInfinite:
				if getattr(self.func, '_infinite', False):
					self = None
				else:
					raise AssertionError("'StopInfinite' exception used only for infinite functions")
			except BaseException as e:
				self.set_exception(e)
			else:
				self.set_result(result)

		def reset(self):
			self._state = "PENDING"
			self._result = None
			self._exception = None
			return self

		def __repr__(self):
			return super().__repr__().replace(self.__class__.__name__, "Future")

	STANDART = 0
	INFINITE = 1

	_queue: Queue = Queue()
	_infinite: Queue = Queue()
	_max_workers: int = 8
	_workers: set[Thread] = set()

	def __init__(self, *, max_workers: int = _max_workers):
		assert max_workers > 0, "'max_workers' must more than zero"
		self._max_workers = max_workers
		self.initialize()
		atexit.register(self.shutdown)

	def initialize(self):
		if bool(self):
			return self

		for _ in range(max(self._max_workers, 1)):
			worker = Thread(target=self._worker, daemon=True)
			worker.start()
			self._workers.add(worker)

		worker = Thread(target=self._worker, args=(Executor.INFINITE,), daemon=True)
		worker.start()
		self._workers.add(worker)

		return self

	def shutdown(self, wait: bool = True):
		assert bool(self), "Already shutdowned or not initialized yet"

		if wait:
			for t in self._workers:
				t.join(timeout=1/(10 * self._max_workers))

		self._workers.clear()

	def _worker(self, worker_type: int = STANDART):
		queue = self._infinite if worker_type == Executor.INFINITE else self._queue
		loop = asyncio.new_event_loop()
		while True:
			item = queue.get()
			item.run(loop)
			if worker_type == Executor.INFINITE and item != None:
				queue.put(item.reset())
				continue
		loop.close()

	@staticmethod
	def build(obj: Function, *args, **kwargs):
		spec = inspect.getfullargspec(obj)
		func = int(inspect.ismethod(obj) or inspect.isclass(obj))
		kw, _args, _kwargs, _default = spec.kwonlydefaults or {}, spec.args or [], \
									   spec.kwonlyargs or [], spec.defaults or []

		ar = [
			kwargs.get(k, v) or d
			for k, v, d in zip(
				_args[func:],
				list(args) + [None] * (len(_args) - len(args)),
				[None] * (len(_args) - len(_default) - func) + list(_default)
			)
		]
		if spec.varargs:
			ar += list(args[len(_args) - func:])

		kw.update({
			k: kwargs[k]
			for k in _kwargs if k in kwargs
		})
		if spec.varkw:
			kw.update({
				k: kwargs[k]
				for k in kwargs.keys()
				if k not in _args
			})

		del spec, func, _args, _kwargs, _default

		return [obj, ar, kw]

	def _create_item(self, func: Function, *args, **kwargs):
		item = self._Item(*self.build(func, *args, **kwargs))
		if getattr(func, '_infinite', False):
			self._infinite.put(item)
			return None
		
		self._queue.put(item)
		return item

	def run(self, funcs: Union[Function, Iterable[Function]], *args, **kwargs):
		funcs = funcs if isinstance(funcs, Iterable) else [funcs]
		assert len(funcs) > 0 and bool(self)
		items = list(filter(bool, map(lambda fn: self._create_item(fn, *args, **kwargs), set(funcs))))

		if len(items) == 0:
			return

		results = []

		try:
			for f in as_completed(items, timeout=30):
				results.append((f.exception() or f.result(), f.func))
		except TimeoutError:
			res_funcs = list(map(lambda res: res[1], results))
			for item in items:
				if item.func not in res_funcs:
					results.append((item, item.func))

		return results if len(results) > 1 else results[0]


	__call__ = run

	def __bool__(self):
		return len(self._workers) > 0

	def __enter__(self):
		return self.initialize()

	def __exit__(self, *args):
		self.shutdown()

	async def __aenter__(self):
		return self.__enter__()

	async def __aexit__(self, *args):
		self.__exit__(*args)


_global_executor = Executor()
build = Executor.build


def init(max_workers: int = 8):
	global _global_executor
	_global_executor = Executor(max_workers=max_workers)
	return _global_executor


def run(funcs: Union[Function, Iterable[Function]], *args, **kwargs):
	return _global_executor(funcs, *args, **kwargs)


def _stop():
	raise StopInfinite()


def infinite(func: Function):
	func._infinite = True
	return func


infinite.stop = _stop


def _repr_(func: Function):
	def __repr():
		return f"<{func.__name__}{inspect.signature(func)}>"

	func.__repr__ = __repr

	return func


def get_pattern(string):
	last, pattern = 0, ""
	for match in re.finditer("[*]+", string):
		l = match.end() - match.start()
		pattern += f"{re.escape(string[last:match.start()])}(." + ("{" + l + "})" if l > 1 else "+)")
		last = match.end()
	pattern += re.escape(string[last:])
	del l, last
	return pattern


class Dispatcher:
	_events: dict[str, set[Function]] = {"*": set()}
	_patterns: dict[str, re.Pattern] = {"*": re.compile(get_pattern("*"))}

	def __init__(self, *dispatchers: Iterable[tuple[str, Iterable[Function]]]):
		if dispatchers:
			self.add_events(dispatchers)

	def add_events(self, *dispatchers: Iterable[tuple[str, Iterable[Function]]]):
		for dispatcher in dispatchers:
			for event, funcs in dispatcher:
				self.add_event(event, funcs)

	def add_event(self, event: str, funcs: Union[Function, Iterable[Function]]):
		ev = self._events.setdefault(event, set())
		funcs = funcs if isinstance(funcs, Iterable) else [funcs]
		ev.update(funcs)
		ptr = get_pattern(event)
		if ptr != event:
			self._patterns.setdefault(event, re.compile(ptr))
		del ptr
		return type(funcs)(map(_repr_, funcs))

	def on(self, event_or_func: Optional[Union[str, Function]], *, can_be_called: bool = True):
		def wrapper(func: Function):
			event = getattr(event_or_func, "__name__", event_or_func) or func.__name__
			self.add_event(event, func)

			if can_be_called:
				return func
			elif inspect.iscoroutinefunction(func):
				async def wrapped(*args, **kwargs):
					return

				wrapped.__name__ = func.__name__
				wrapped.__repr__ = func.__repr__

				return wrapped
			else:
				def wrapped(*args, **kwargs):
					return

				wrapped.__name__ = func.__name__
				wrapped.__repr__ = func.__repr__

				return wrapped

		return wrapper if isinstance(event_or_func, (str, type(None))) else wrapper(event_or_func)

	def dispatch(self, event: str, *args, **kwargs):
		funcs = self._events.get(event, set()).copy()
		patterned = set()
		for ev, ptr in self._patterns.items():
			m = ptr.fullmatch(event)
			if m:
				patterned.update([m.group(1)])
				funcs.update(self._events.get(ev))
		if len(patterned) > 1:
			patterned.discard(event)
		patterned = list(patterned)
		kwargs["patterned"] = patterned if len(patterned) > 1 else patterned.pop(0)
		return run(funcs, args, kwargs)

	def dispatcher(self, event_or_func: Optional[Union[str, Function]], *, dispatcher_first: bool = True):
		def wrapper(func: Function):
			event = getattr(event_or_func, "__name__", event_or_func) or func.__name__

			if dispatcher_first:
				name = func.__name__
				def wrapped(*args, **kwargs):
					kwargs[f"{name}__args"] = run(func, args, kwargs)
					return (kwargs[f"{name}__args"], self.dispatch(event, args, kwargs))
			else:
				def wrapped(*args, **kwargs):
					kwargs[f"{event}__args"] = self.dispatch(event, args, kwargs)
					return (run(func, args, kwargs), kwargs[f"{event}__args"])

			if inspect.iscoroutinefunction(func):
				async def _wrapped_(*args, **kwargs):
					return wrapped(*args, **kwargs)

				_wrapped_.__name__ = func.__name__
				_wrapped_.__repr__ = func.__repr__

				return _wrapped_

			wrapped.__name__ = func.__name__
			wrapped.__repr__ = func.__repr__

			return wrapped

		return wrapper if isinstance(event_or_func, (str, type(None))) else wrapper(event_or_func)

	def __contains__(self, event: str):
		return event in self._events

	def __hash__(self):
		return id(self)

	def __iter__(self):
		return iter(self._events.items())

	def __format__(self, spec: str):
		if spec in ['e', 'events']:
			return ' ; '.join(self._events.keys())
		elif spec in ['p', 'ptr', 'patterns']:
			return ' ; '.join(self._patterns.keys())

		return repr(self)

	def __str__(self):
		return repr(self)

	def __repr__(self):
		events = list(self._events.keys())
		patterns = list(self._patterns.keys())
		return f"<Dispatcher {events=}, {patterns=}>"


class Loader:
	__loaders__: dict[str, "Loader"] = {}
	__fields__: dict[str, str] = {}

	@classmethod
	def load(cls, data: Union[str, dict, Any]):
		if isinstance(data, dict) and data.get("_", None) in Loader.__loaders__:
			obj = Loader.__loaders__.get(data.pop("_"), cls)
			obj = run(obj, **{k: data.get(k, None) for k in obj.__fields__.keys()})[0]

			for a, k in obj.__fields__.items():
				if hasattr(obj, k):
					dt = data.get(a, getattr(obj, k, None))
					try:
						if isinstance(dt, dict):
							dt = Loader.load(dt)
						elif isinstance(dt, Iterable):
							dt = type(dt)(map(Loader.load, dt))
					finally:
						setattr(obj, k, dt)

			return obj
		elif isinstance(data, str):
			return cls.load(loads(data))
		
		return data

	@property
	def __dict__(self):
		return {"_": self.__class__.__name__, **dict(iter(self))}

	def __iter__(self):
		yield from [(a, getattr(self, k, None)) for a, k in self.__fields__.items() if hasattr(self, k)]

	@staticmethod
	def _get_subclasses_(cls):
		return set(cls.__subclasses__()).union([s for c in cls.__subclasses__() for s in cls._get_subclasses_(c)])

	def __init_subclass__(cls, **kwargs):
		cls.__fields__.update(kwargs.get("fields", {}))
		Loader.__loaders__ = {o.__name__: o for o in Loader._get_subclasses_(Loader)}
		super(Loader, cls).__init_subclass__(**kwargs)


if __name__ == '__main__':
	@infinite
	async def test():
		print("test1")

	async def test_with_args(*args):
		print(*args)

	run([test, test_with_args])
