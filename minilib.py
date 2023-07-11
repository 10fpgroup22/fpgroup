import asyncio
import atexit
import inspect
import logging
import re

from collections import deque
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
	fmt="[%(asctime)s %(levelname)s] %(message)s",
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
					raise
				self.set_exception(AssertionError("'StopInfinite' exception used only for infinite functions"))
			except BaseException as e:
				self.set_exception(e)
				return e
			else:
				self.set_result(result)
				return result

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
	_initialized: bool = False
	_max_workers: int = 8
	_workers: set[Thread] = set()

	def __init__(self, *, max_workers: int = _max_workers, timeout: float = 30):
		assert max_workers > 1, "'max_workers' must more than one"
		self._max_workers = max_workers
		self._idle = [True] * (max_workers - 1)
		self._timeout = timeout
		self.initialize()
		atexit.register(self.shutdown)

	@property
	def max_workers(self):
		return self._max_workers

	@property
	def timeout(self):
		return self._timeout
	
	@timeout.setter
	def timeout(self, value: float):
		self._timeout = float(value)

	def initialize(self):
		if bool(self):
			return self

		for x in range(max(self.max_workers - len(self._workers), 2)):
			buf = x == self.max_workers
			if x < self.max_workers - 1:
				self._idle[x] = True
			worker = Thread(target=self._worker, args=(int(buf), x), daemon=True)
			worker.start()
			self._workers.add(worker)

		self._initialized = True

		return self

	def shutdown(self, wait: bool = True):
		assert bool(self), "Already shutdowned or not initialized yet"
		self._initialized = False

		if wait:
			for t in self._workers:
				t.join(timeout=1/self._max_workers)

		self._workers.clear()

		return self

	def _worker(self, worker_type: int = STANDART, index: int = 0):
		queue = self._infinite if worker_type == Executor.INFINITE else self._queue
		cond = index < self.max_workers - 1
		loop = asyncio.new_event_loop()
		while self._initialized:
			item = queue.get()
			try:
				item.run(loop)
			except StopInfinite:
				continue
			if worker_type == Executor.INFINITE:
				queue.put(item.reset())
		loop.close()

	@staticmethod
	def build(obj: Function, *args, **kwargs) -> list[Function, deque, dict]:
		spec = inspect.getfullargspec(obj)
		func = int(inspect.ismethod(obj) or inspect.isclass(obj))
		kw, _args, _kwargs, _default = spec.kwonlydefaults or {}, spec.args or [], \
									   spec.kwonlyargs or [], spec.defaults or []

		ar = deque(
			kwargs.get(k, v) or d
			for k, v, d in zip(
				_args[func:], list(args),
				[None] * (len(_args) - len(_default) - func) + list(_default)
			)
		)

		if spec.varargs and len(args) - func > len(_args):
			ar.extend(args[len(_args) - func:])

		kw.update({k: v for k, v in kwargs.items() if k in _kwargs})

		if spec.varkw:
			kw.update({k: v for k, v in kwargs.items() if k not in _args})

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
		assert bool(self), "call .initialize() first"
		funcs = set(funcs if isinstance(funcs, Iterable) else [funcs])
		assert len(funcs) > 0, "the 'funcs' argument should not be empty"
		items = list(filter(None, map(lambda fn: self._create_item(fn, *args, **kwargs), funcs)))

		if len(items) == 0:
			del items, funcs
			return

		results = []

		try:
			for f in as_completed(items, timeout=30):
				results.append((f.exception() or f.result(), f))
		except TimeoutError:
			fns = items - list(map(lambda res: res[1], results))
			for item in fns:
				results.append((item, item))

		del items, funcs

		return results if len(results) > 1 else results[0]

	__call__ = run

	def __bool__(self):
		return len(self._workers) == self._max_workers and self._initialized

	def __enter__(self):
		return self.initialize()

	def __exit__(self, *args):
		self.shutdown()

	async def _wait_(self):
		while not all(self._idle):
			pass
		return True

	def __await__(self):
		return self._wait_().__await__()

	async def __aenter__(self):
		return self.__enter__()

	async def __aexit__(self, *args):
		self.__exit__(*args)

	def __repr__(self):
		return f'<{self.__class__.__name__} initialized={self._initialized} workers={len(self._workers)}>'


_global_executor = Executor()
build = Executor.build


def init(max_workers: int = _global_executor.max_workers):
	global _global_executor
	if max_workers != _global_executor.max_workers:
		_global_executor = Executor(max_workers=max_workers)
	return _global_executor


def run(funcs: Union[Function, Iterable[Function]], *args, **kwargs):
	return _global_executor(funcs, *args, **kwargs)


def _stop_():
	raise StopInfinite()


def infinite(func: Function):
	func._infinite = True
	func.stop = _stop_
	return func


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
	del last
	return pattern


class Dispatcher:
	_events: dict[str, set[Function]] = {"*": set()}
	_patterns: dict[str, re.Pattern] = {"*": re.compile(get_pattern("*"))}
	_executor: Executor = _global_executor

	def __init__(self, *dispatchers: Iterable[tuple[str, Iterable[Function]]], max_workers: int = _global_executor.max_workers):
		if dispatchers:
			self.add_events(dispatchers)
		if max_workers != self._executor.max_workers:
			self._executor = Executor(max_workers=max_workers)

	def add_events(self, *dispatchers: Iterable[tuple[str, Iterable[Function]]]):
		for dispatcher in dispatchers:
			for event, funcs in dispatcher:
				self.add_event(event, funcs)

	def add_event(self, event: str, funcs: Union[Function, Iterable[Function]]):
		funcs = funcs if isinstance(funcs, Iterable) else [funcs]
		assert len(funcs) > 0, "the 'funcs' argument should not be empty"
		_funcs = set(filter(lambda f: not getattr(f, '_infinite', False), funcs))
		assert len(_funcs) > 0, "the 'funcs' argument should not only consist of infinite functions"
		ev = self._events.setdefault(event, set())
		ev.update(_funcs)
		ptr = get_pattern(event)
		if ptr != event:
			self._patterns.setdefault(event, re.compile(ptr))
		del ptr
		return type(funcs)(map(_repr_, _funcs))

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

			def wrapped(*args, **kwargs):
				return

			wrapped.__name__ = func.__name__
			wrapped.__repr__ = func.__repr__

			return wrapped

		return wrapper if isinstance(event_or_func, (str, type(None))) else wrapper(event_or_func)

	event = lambda self, f: self.on(f)
	event.__name__ = '<event>'

	def dispatch(self, event: str, *args, **kwargs):
		funcs = self._events.get(event, set()).copy()
		patterned = set()
		for ev, ptr in self._patterns.items():
			m = ptr.fullmatch(event)
			if m:
				patterned.update([m.group(1)])
				funcs.update(self._events.get(ev))
		if len(funcs) == 0:
			del patterned, funcs
			return
		elif len(patterned) > 1:
			patterned.discard(event)
		patterned = list(patterned)
		kwargs["patterned"] = patterned.pop(0) if len(patterned) == 1 else patterned
		return self._executor(funcs, *args, **kwargs)

	def dispatcher(self, event_or_func: Optional[Union[str, Function]], *, dispatcher_first: bool = True):
		def wrapper(func: Function):
			event = getattr(event_or_func, "__name__", event_or_func) or func.__name__

			if dispatcher_first:
				name = func.__name__
				def wrapped(*args, **kwargs):
					kwargs[f"{name}__args"] = self._executor(func, *args, **kwargs)
					return (kwargs[f"{name}__args"], self.dispatch(event, *args, **kwargs))
			else:
				def wrapped(*args, **kwargs):
					kwargs[f"{event}__args"] = self.dispatch(event, *args, **kwargs)
					return (self._executor(func, *args, **kwargs), kwargs[f"{event}__args"])

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
			return '\n'.join(self._events.keys())
		elif spec in ['p', 'ptr', 'patterns']:
			return '\n'.join(self._patterns.keys())

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
						if isinstance(dt, (dict, str)):
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
	async def test():
		for x in range(20):
			await asyncio.sleep(.1)
			print(f"Iteration x={x + 1}: idle={_global_executor._idle}", flush=True)

	async def test1():
		print("test1", flush=True)
		return await test()

	async def test2():
		print("test2", flush=True)
		return await test()

	async def main():
		return await _global_executor

	run([test, test1, test2])
	print(asyncio.run(main()))
