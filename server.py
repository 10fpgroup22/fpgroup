import asyncio
import atexit
import deps
import minilib

from aiohttp import web, ClientSession
from os import getenv

app = web.Application()
env = deps.setup(app, ['en_US', 'ru_RU', 'uk_UA'])
env.add_extension("jinja2.ext.debug")

routes = web.RouteTableDef()


@routes.get('/')
@deps.template('index.html')
async def index(request):
	return


@routes.get('/streams')
@deps.template('streams.html')
async def streams(request):
	return


@routes.get('/auth')
@deps.template('auth.html')
async def auth(request):
	return


@routes.post('/auth')
async def auth(request):
	data = await request.post()


@routes.get('/auth/telegram')
async def auth_telegram(request):
	data = request.query
	user = User.from_telegram(data.get('id', None))
	if user:
		pass


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
		app['domains'].extend(resp)
		del resp
	print(f"Domains: {' , '.join(' -> '.join(x) for x in app['domains'])}", flush=True)
	get_domain.stop()


async def run(block: bool = False):
	PORT = getenv("PORT", 8080)
	app.add_routes(routes)

	app['domains'] = []
	ngrok = minilib.run([get_domain, asyncio.create_subprocess_shell], f"ngrok http localhost:{PORT} --log=stdout", stdout=asyncio.subprocess.PIPE)[0]
	atexit.register(ngrok.kill)

	runner = web.AppRunner(app)
	await runner.setup()
	site = web.TCPSite(runner, 'localhost', PORT)
	await site.start()

	while block:
		await asyncio.sleep(.1)

	return app

if __name__ == '__main__':
	asyncio.run(run(True))
