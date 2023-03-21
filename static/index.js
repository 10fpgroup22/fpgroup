function setCookie(name, value, expires){
	let date = new Date();
	date.setTime(date.getTime() + (expires * 24 * 60 * 60 * 1000));
	document.cookie = `${name}=${value};expires=${expires};path=/`;
}

function redirect(el){
	setCookie("LANGUAGE", el.name, 365);
	window.location.reload()
}