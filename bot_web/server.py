import asyncio

from .minilib import *

path = realpath(dirname(__file__))

app = web.Application()
setup(app, static=join(path, "static"), templates=join(path, "templates"))
routes = web.RouteTableDef()


@routes.get('/')
@template('index.html')
def index(request):
	pass


@routes.get('/login')
@template('logreg.html')
def login(request):
	return {'title': 'Вход'}


@routes.post('/login')
async def login_callback(request):
	data = await request.post()


@routes.get('/register')
@template('logreg.html')
def register(request):
	return {'title': 'Регистрация'}


@routes.post('/register')
async def register_callback(request):
	data = await request.post()


@routes.get('/telegram')
@template("index.html")
async def telegram(request):
	data = request.query
	print(data)


async def run(block=True):
	runner = web.AppRunner(app)
	await runner.setup()
	site = web.TCPSite(runner, 'localhost', 8080)
	await site.start()
	if block:
		while True:
			await asyncio.sleep(1)


app.add_routes(routes)


if __name__ == '__main__':
	asyncio.run(run())
