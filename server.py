import asyncio
import atexit
import deps
import minilib

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


async def shutdown(_):
	app['ngrok'].kill()


async def get_domain():
	async with ClientSession() as s:
		while True:
			resp = []
			await asyncio.sleep(1)
			try:
				async with s.get("http://127.0.0.1:4040/api/tunnels") as r:
					resp = list(map(
						lambda x: (x['config']['addr'], x['public_url']), (await r.json()).get('tunnels', [])
					))

				assert len(resp) > 0
			except (TimeoutError, AssertionError):
				continue
			app['domains'] = resp
			logger.info(f"Domains: {','.join(' -> '.join(x) for x in resp)}")
			del resp
			break


async def run(block: bool = False, *, log_enabled: bool = False):
	PORT = getenv("PORT", 8080)
	app.add_routes(routes)
	app['ngrok'] = Popen(["ngrok", "http", f"localhost:{PORT}", "--log=stdout"], stdout=PIPE)
	minilib.run(get_domain)

	runner = web.AppRunner(app)
	await runner.setup()
	site = web.TCPSite(runner, 'localhost', PORT)
	await site.start()

	if block:
		while True:
			await asyncio.sleep(.1)

	return app

if __name__ == '__main__':
	asyncio.run(run(block=True))
