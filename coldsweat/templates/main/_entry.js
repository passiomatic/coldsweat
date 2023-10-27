const mainFragment = `{% include "main/_entry.html" %}`
const navFragment = `{% include "main/_nav.html" %}`
var mainEl = document.getElementById('main');
var navEl = document.getElementById('nav');
mainEl.innerHTML = mainFragment;
Sweat.morph(navEl, navFragment);