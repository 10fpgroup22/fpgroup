import aiohttp_jinja2 as aiojinja

from aiohttp import web, hdrs
from jinja2 import FileSystemLoader, pass_context
from os.path import realpath, dirname, join
from typing import Optional, Union, Type

APP_KEY = "aiojinja2"
PATH = realpath(dirname(__name__))


def template(template: str, *, app_key=APP_KEY, encoding: str = "utf-8", status: int = 200):
	return aiojinja.template(template, app_key=app_key, encoding=encoding, status=status)


@pass_context
def url_for(context, route: str, query_: Optional[dict[str, str]] = None, **kwargs: Union[str, int]):
	app: web.Application = context["app"]
	routes = dict(filter(bool, map(lambda x: ((x.name or x.handler.__name__, x.url_for)
											  if x.method in hdrs.METH_ALL else None),
								   app.router.routes())))
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


async def processor(request):
	return {'path': request.rel_url}


def setup(app: web.Application, *, app_key: str = APP_KEY, static: str = "static", templates: str = "templates"):
	templates = FileSystemLoader([templates] if isinstance(templates, str) else templates) if templates else None
	app.router.add_static(f"/static", static, name='static')

	env = aiojinja.setup(app, app_key=app_key, loader=templates, context_processors=[processor], default_helpers=False)
	env.globals["url_for"] = url_for

	return env
