import asyncio
import aiohttp_jinja2 as aiojinja

from aiohttp import web, hdrs
from babel.core import Locale
from babel.support import Translations
from jinja2 import FileSystemLoader, pass_context, select_autoescape
from minilib import Loader, logger
from os.path import exists, abspath, dirname, join
from typing import Any, Optional, Union, Type

APP_KEY = "aiojinja2"

if not hasattr(asyncio, 'coroutine'):
	import inspect

	def coroutine(func):
		if inspect.iscoroutinefunction(func):
			return func

		async def wrapper(*args, **kwargs):
			return func(*args, **kwargs)

		wrapper.__name__ = func.__name__
		wrapper.__repr__ = func.__repr__

		return wrapper

	asyncio.coroutine = coroutine


def template(template: str, *, app_key: str = APP_KEY, encoding: str = "utf-8", status: int = 200):
	return aiojinja.template(template, app_key=app_key, encoding=encoding, status=status)


@web.middleware
async def request_handler(req, handler):
	resp = await handler(req)
	logger.info(f"[{req.remote}] {req.method} {req.url} - {resp.status}")
	return resp


@pass_context
def url_for(context, route: str, query_: Optional[dict[str, str]] = None, **kwargs: Union[str, int]):
	app: web.Application = context["app"]
	routes = dict(filter(bool, map(
		lambda x: (
			(x.name or x.handler.__name__, x.url_for) if x.method in hdrs.METH_ALL else None
		), app.router.routes()
	)))
	parts: dict[str, str] = {}
	for key, val in kwargs.items():
		if isinstance(val, (str, int)):
			parts[key] = str(val)
		else:
			raise TypeError(f"argument should be str or int, got {key} -> [{type(val)}] {val}")

	url = routes[route](**parts)
	if query_:
		url = url.with_query(query_)

	return url


@pass_context
def gettext(context, message):
	langs, locale = context['languages'], context['locale']
	return langs.get((locale.language, locale.language_name.capitalize())).ugettext(message)


@pass_context
def ngettext(context, message, plural, count):
	langs, locale = context['languages'], context['locale']
	return langs.get((locale.language, locale.language_name.capitalize())).ungettext(message, plural, count)


async def processor(request):
	locale = request.cookies.get('LANGUAGE', request.headers.get('ACCEPT-LANGUAGE', 'en'))[:2]
	return {'path': request.rel_url, 'locale': Locale.parse(locale)}


def setup(app: web.Application, languages: list[str], *, app_key: str = APP_KEY, static: str = "static", templates: str = "templates", locales_path: str = 'locales'):
	templates = FileSystemLoader([templates] if isinstance(templates, str) else templates) if templates else None
	app.router.add_static("/static", static, name='static')
	app.middlewares.append(request_handler)

	languages = list(map(Locale.parse, languages))

	env = aiojinja.setup(app, app_key=app_key, loader=templates,
						 context_processors=[processor], default_helpers=False,
						 extensions=['jinja2.ext.i18n'])
	env.globals['languages'] = {(lang.language, lang.language_name.capitalize()): Translations.load(locales_path, lang) for lang in languages}
	env.globals["url_for"] = url_for
	env.install_gettext_callables(gettext, ngettext)

	return env


class Settings(Loader):
	__fields__ = {"groups": "_groups"}

	def __init__(self):
		self._groups = {}

	def add(self, group: str):
		self[group] = {}
		return self[group]

	def set(self, group: str, name: str, value: Any):
		self[group, name] = value
		return value

	def remove(self, group: str, name: Optional[str] = None):
		del self[group, name], group, name

	def get(self, group: str, name: Optional[str] = None):
		return self[group, name]

	def iter_group(self, group: str):
		return self._groups.get(group, {}).items()

	def __getitem__(self, item: Union[str, tuple]):
		group, name = item if isinstance(item, tuple) else [item, None]

		if not (type(group) == str and type(name) in [str, type(None)]):
			raise TypeError(f"Failed to get '{name}' of '{group}'. Check for type 'item' attribute")

		if name:
			return self._groups.get(group, {}).get(name, None)

		return self._groups.get(group, {})

	def __delitem__(self, item: Union[str, tuple]):
		group, name = item if isinstance(item, tuple) else [item, None]

		if not (type(group) == str and type(name) in [str, type(None)]):
			raise TypeError(f"Failed to delete '{name}' of '{group}'. Check for type 'item' attribute")

		if name:
			del self._groups[group][name]
		else:
			del self._groups[group]

	def __setitem__(self, item: Union[str, tuple], value: Any):
		group, name = item if isinstance(item, tuple) else [item, None]

		if not (type(group) == str and type(name) == str):
			raise TypeError(f"Failed to set '{name}' of '{group}'. Check for type 'item' attribute")

		grp = self._groups.setdefault(group, {})
		grp[name] = value
