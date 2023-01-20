from .minilib import *
from os import getenv

__all__ = ["run"]

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
	from pyngrok import ngrok, conf
	from socket import socket, SOCK_DGRAM

	s = socket(type=SOCK_DGRAM)
	ngconf = conf.PyngrokConfig(ngrok_version="v3", auth_token=getenv("NGROK"))

	try:
		s.connect(('10.255.255.255', 1))
		ip = s.getsockname()[0]
	except:
		ip = '127.0.0.1'

	runner = web.AppRunner(app)
	await runner.setup()
	site = web.TCPSite(runner, ip, 8080)
	await site.start()

	tunnel_ip = ngrok.connect(site.name, pyngrok_config=ngconf).public_url
	print(f"Local ip: {site.name}\nGlobal ip: {tunnel_ip}")

	if block:
		while True:
			await asyncio.sleep(1)

	return site


app.add_routes(routes)


if __name__ == '__main__':
	asyncio.run(run())
