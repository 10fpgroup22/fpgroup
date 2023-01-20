import asyncio
import inspect
import re

from concurrent.futures import ThreadPoolExecutor, Executor
from json import loads
from typing import Any, Optional, Union, Iterable, Coroutine, Callable

__all__ = ["Dispatcher", "Loader", "Function", "build", "get_pattern", "run"]

Function = Union[Callable, Coroutine]
_global_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="Builder-")


def _repr_(func: Function):
	def __repr():
		return f"{func.__name__}{inspect.signature(func)}"

	func.__repr__ = __repr

	return func


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
		k: kwargs.get(k, kw.get(k, None))
		for k in _kwargs
	})
	if spec.varkw:
		kw.update({
			k: kwargs.get(k, kw.get(k, None))
			for k in kwargs.keys()
			if k not in _args
		})

	del spec, func, _args, _kwargs, _default

	return [obj, ar, kw]


def _run_(func: Coroutine, *args, **kwargs):
	return asyncio.run(func(*args, **kwargs))


def run(funcs: Union[Function, Iterable[Function]], *args, executor: Executor = _global_executor, **kwargs):
	results = []
	funcs = list(map(lambda fn: (build(fn, *args, **kwargs)),
				 (funcs if isinstance(funcs, Iterable) else [funcs])))

	for fn, ar, kw in funcs:
		coro = bool(inspect.iscoroutine(fn) or inspect.iscoroutinefunction(fn))
		res = executor.submit(_run_, fn, *ar, **kw) if coro else executor.submit(fn, *ar, **kw)
		try:
			res = res.result(timeout=5)
		except TimeoutError:
			pass
		finally:
			results.append((res, fn))

	del funcs
	return results if len(results) != 1 else results[0]


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
	_executor: Executor = _global_executor

	def __init__(self, *dispatchers: Iterable[tuple[str, Iterable[Function]]], executor: Executor = _global_executor):
		self._executor = executor
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

		if inspect.iscoroutinefunction(event_or_func):
			async def _wrapper_(func: Function):
				return wrapper(func)

			_wrapper_.__name__ = wrapper.__name__
			_wrapper_.__repr__ = wrapper.__repr__

			return run(_wrapper_, event_or_func, executor=self._executor)

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
		return run(funcs, args, kwargs, executor=self._executor)

	def dispatcher(self, event_or_func: Optional[Union[str, Function]], *, dispatcher_first: bool = True):
		def wrapper(func: Function):
			event = getattr(event_or_func, "__name__", event_or_func) or func.__name__

			if dispatcher_first:
				name = func.__name__
				def wrapped(*args, **kwargs):
					kwargs[f"{name}__args"] = run(func, args, kwargs, executor=self._executor)
					return (kwargs[f"{name}__args"], self.dispatch(event, args, kwargs))
			else:
				def wrapped(*args, **kwargs):
					kwargs[f"{event}__args"] = self.dispatch(event, args, kwargs)
					return (run(func, args, kwargs, executor=self._executor), kwargs[f"{event}__args"])

			if inspect.iscoroutinefunction(func):
				async def _wrapped_(*args, **kwargs):
					return wrapped(*args, **kwargs)

				_wrapped_.__name__ = func.__name__
				_wrapped_.__repr__ = func.__repr__

				return _wrapped_

			wrapped.__name__ = func.__name__
			wrapped.__repr__ = func.__repr__

			return wrapped

		if inspect.iscoroutinefunction(event_or_func):
			async def _wrapper_(func: Function):
				return wrapper(func)

			_wrapper_.__name__ = wrapper.__name__
			_wrapper_.__repr__ = wrapper.__repr__

			return run(_wrapper_, event_or_func, executor=self._executor)

		return wrapper if isinstance(event_or_func, (str, type(None))) else wrapper

	def __contains__(self, event: str):
		return event in self._events

	def __hash__(self):
		return id(self)

	def __iter__(self):
		return iter(self.__events.items())

	def __format__(self, spec: str):
		if spec in ['e', 'events']:
			return ' , '.join(self._events.keys())
		elif spec in ['p', 'ptr', 'patterns']:
			return ' , '.join(self._patterns.keys())

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
			obj = Loader.__loaders__.get(data["_"], cls)
			obj = run(obj, kwargs={k: data.get(k, data.get(x[x.index(k) - 1], None)) for x in obj.__fields__.items() for k in x})[0]

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
		return {"_": self.__class__.__name__, **{a: getattr(self, k, None) for a, k in self.__fields__.items() if hasattr(self, k)}}

	def __iter__(self):
		return iter([(k, getattr(self, k, None)) for k in self.__fields__.values() if hasattr(self, k)])

	@staticmethod
	def _get_subclasses_(cls):
		return set(cls.__subclasses__()).union([s for c in cls.__subclasses__() for s in cls._get_subclasses_(c)])

	def __init_subclass__(cls, **kwargs):
		cls.__fields__.update(kwargs.get("fields", {}))
		Loader.__loaders__ = {o.__name__: o for o in Loader._get_subclasses_(Loader)}
		super(Loader, cls).__init_subclass__(**kwargs)
