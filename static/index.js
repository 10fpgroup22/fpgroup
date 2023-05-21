function setCookie(name, value, expires=1){
	let date = new Date();
	date.setTime(date.getTime() + (expires * 24 * 60 * 60 * 1000));
	let cookie = `${name}=${value};expires=${date.toUTCString()};path=/;SameSite=Strict`
	document.cookie = cookie;
}

function toggleDarkMode(){
	let body = document.body;
	body.classList.toggle('dark');
	setCookie("DARKMODE", body.classList.contains('dark'))
}

function set_language({name}){
	setCookie("LANGUAGE", name, 30);
	window.location.reload();
}

function auth_submit(form){
	let {username, password} = Object.fromEntries(new FormData(form).entries());
	if(username !== "" && password !== ""){
		let origin = document.location.origin, reason = form.querySelector('p.reason');
		submitter = new XMLHttpRequest();
		submitter.onload = function(){
			try{
				data = JSON.parse(this.responseText);
				switch(data['type']){
					case 'redirect': document.location.assign(origin + data['url']); break;
					case 'reset': form['password'].value = ''; reason.innerHTML = data['reason'].join('<br>'); reason.style.display = 'block'; break;
					default: break;
				}
			} catch(e){
				console.error('Something went wrong', e);
			}
		}
		submitter.open("POST", origin + "/auth");
		submitter.send(JSON.stringify({username, password}));
	}
	return false;
}