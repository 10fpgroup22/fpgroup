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


async def run():
	app.add_routes(routes)
	runner = web.AppRunner(app)
	await runner.setup()
	site = web.TCPSite(runner, 'localhost', getenv("PORT", 8080))
	await site.start()

	ngrok = Popen(["ngrok", "http", site.name], stdout=PIPE)
	atexit.register(ngrok.kill)
	await asyncio.sleep(3)

	async with ClientSession() as s:
		try:
			async with s.get(f"http://127.0.0.1:4040/api/tunnels") as r:
				resp = list(map(
					lambda t: logger.info(f"{t['config']['addr']} -> {t['public_url']}"),
					(await r.json()).get('tunnels', [])
				))
				del resp
		except:
			pass

	return app

if __name__ == '__main__':
	asyncio.run(run())
