import asyncio
import atexit
import deps
import minilib

from aiohttp import web, ClientSession
from gettext import gettext as _
from minilib import logger
from os import getenv
from threading import Condition

app = web.Application()
deps.setup(app)
routes = web.RouteTableDef()


@routes.get('/')
@deps.template('index.html')
async def index(request):
	return


@routes.get('/streams')
@deps.template('streams.html')
async def streams(request):
	return


@minilib.infinite
async def get_domain():
	async with ClientSession() as s:
		resp = []
		await asyncio.sleep(1)
		try:
			async with s.get("http://127.0.0.1:4040/api/tunnels") as r:
				resp = list(map(
					lambda x: (x['config']['addr'], x['public_url']), (await r.json()).get('tunnels', [])
				))

			assert len(resp) > 0
		except (TimeoutError, AssertionError) as err:
			print(err.reason)
			return
		app['domains'] = resp
		del resp
	minilib.infinite.stop()


async def run(log_enabled: bool = False):
	PORT = getenv("PORT", 8080)
	app.add_routes(routes)

	runner = web.AppRunner(app)
	await runner.setup()
	site = web.TCPSite(runner, 'localhost', PORT)
	await site.start()
	ngrok = await asyncio.create_subprocess_shell(f"ngrok http localhost:{PORT} --log=stdout", stdout=asyncio.subprocess.PIPE)
	atexit.register(ngrok.kill)

	minilib.run(get_domain)

	return app

if __name__ == '__main__':
	asyncio.run(run(block=True))
