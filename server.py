import asyncio
import deps
import minilib

from aiohttp import web, ClientSession
from gettext import gettext as _
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


@routes.get('/streams')
@deps.template('streams.html')
async def streams(request):
	return


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
			except (TimeoutError, AssertionError) as err:
				print(err.reason)
				continue
			app['domains'] = resp
			print(f"Domains: {' -> '.join(x for x in resp)}")
			del resp
			break


async def run(log_enabled: bool = False):
	PORT = getenv("PORT", 8080)
	app.add_routes(routes)
	minilib.register_exit(Popen(["ngrok", "http", f"localhost:{PORT}", "--log=stdout"], stdout=PIPE).kill)
	minilib.run(get_domain)

	runner = web.AppRunner(app)
	await runner.setup()
	site = web.TCPSite(runner, 'localhost', PORT)
	await site.start()

	return app

if __name__ == '__main__':
	asyncio.run(run(block=True))
