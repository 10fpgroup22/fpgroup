import asyncio
import atexit
import deps
import logging

from aiohttp import web, ClientSession
from minilib import logger
from os import getenv
from subprocess import Popen, PIPE

app = web.Application()
deps.setup(app)
routes = web.RouteTableDef()


@routes.get('/')
@deps.template('index.html')
async def index(request):
	return


async def run(block: bool = False, *, log_enabled: bool = False):
	app.add_routes(routes)
	runner = web.AppRunner(app)
	await runner.setup()
	site = web.TCPSite(runner, 'localhost', getenv("PORT", 8080))
	await site.start()
	site_path = site.name

	app['ngrok'] = Popen([
		"ngrok", "http", site_path.replace(f"{('https' if site_path.startswith('https://') else 'http')}://", ''), "--log=stdout"],
	stdout=PIPE)
	await asyncio.sleep(3)

	async with ClientSession() as s:
		resp = []
		try:
			async with s.get("http://127.0.0.1:4040/api/tunnels") as r:
				resp = list(map(
					lambda t: logger.info(f"{t['config']['addr']} -> {t['public_url']}"),
					(await r.json()).get('tunnels', [])
				))

			assert len(resp) > 0
		except TimeoutError as e:
			if log_enabled:
				logger.warn(f"<{e}>")
		except AssertionError as e:
			pass

		del resp

	if block:
		while True:
			await asyncio.sleep(.1)

	return app

if __name__ == '__main__':
	asyncio.run(run(block=True))
