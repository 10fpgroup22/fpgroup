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


@routes.get('/live')
async def live_stream(request):
	stream = web.StreamResponse()
	stream.content_type = 'multipart/x-mixed-replace; boundary=frame'
	await stream.prepare(request)

	for frame in live:
		stream.write(frame)

	return stream


@routes.post('/live')
async def stream_live(request):
	return


async def shutdown(_):
	app['ngrok'].kill()


async def get_domain():
	await asyncio.sleep(3)
	async with ClientSession() as s:
		resp = []
		while True:
			try:
				async with s.get("http://127.0.0.1:4040/api/tunnels") as r:
					resp = list(map(
						lambda x: logger.info(f"{x['config']['addr']} -> {x['public_url']}"), (await r.json()).get('tunnels', [])
					))

				assert len(resp) > 0
			except (TimeoutError, AssertionError):
				continue

			break

		del resp


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
