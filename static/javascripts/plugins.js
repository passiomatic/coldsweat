// Avoid `console` errors in browsers that lack a console.
(function() {
var method;
var noop = function () {};
var methods = [
'assert', 'clear', 'count', 'debug', 'dir', 'dirxml', 'error',
'exception', 'group', 'groupCollapsed', 'groupEnd', 'info', 'log',
'markTimeline', 'profile', 'profileEnd', 'table', 'time', 'timeEnd',
'timeStamp', 'trace', 'warn'
];
var length = methods.length;
var console = (window.console = window.console || {});

while (length--) {
method = methods[length];

// Only stub undefined methods.
if (!console[method]) {
console[method] = noop;
}
}
}());

// Place any jQuery/helper plugins in here.

/*! responsive-nav.js v1.0.14 by @viljamis, http://responsive-nav.com, MIT license */
var responsiveNav=function(g,h){var t=!!g.getComputedStyle;g.getComputedStyle||(g.getComputedStyle=function(a){this.el=a;this.getPropertyValue=function(d){var c=/(\-([a-z]){1})/g;"float"===d&&(d="styleFloat");c.test(d)&&(d=d.replace(c,function(a,d,c){return c.toUpperCase()}));return a.currentStyle[d]?a.currentStyle[d]:null};return this});var b,f,e,u=h.documentElement,v=h.getElementsByTagName("head")[0],m=h.createElement("style"),r=!1,j=function(a,d,c,b){if("addEventListener"in a)try{a.addEventListener(d,
c,b)}catch(e){if("object"===typeof c&&c.handleEvent)a.addEventListener(d,function(a){c.handleEvent.call(c,a)},b);else throw e;}else"attachEvent"in a&&("object"===typeof c&&c.handleEvent?a.attachEvent("on"+d,function(){c.handleEvent.call(c)}):a.attachEvent("on"+d,c))},k=function(a,d,c,b){if("removeEventListener"in a)try{a.removeEventListener(d,c,b)}catch(e){if("object"===typeof c&&c.handleEvent)a.removeEventListener(d,function(a){c.handleEvent.call(c,a)},b);else throw e;}else"detachEvent"in a&&("object"===
typeof c&&c.handleEvent?a.detachEvent("on"+d,function(){c.handleEvent.call(c)}):a.detachEvent("on"+d,c))},l=function(a,d){for(var b in d)a.setAttribute(b,d[b])},n=function(a,b){a.className+=" "+b;a.className=a.className.replace(/(^\s*)|(\s*$)/g,"")},p=function(a,b){a.className=a.className.replace(RegExp("(\\s|^)"+b+"(\\s|$)")," ").replace(/(^\s*)|(\s*$)/g,"")},s=function(a,d){var c;this.options={animate:!0,transition:400,label:"Menu",insert:"after",customToggle:"",openPos:"relative",jsClass:"js",
init:function(){},open:function(){},close:function(){}};for(c in d)this.options[c]=d[c];n(u,this.options.jsClass);this.wrapperEl=a.replace("#","");if(h.getElementById(this.wrapperEl))this.wrapper=h.getElementById(this.wrapperEl);else throw Error("The nav element you are trying to select doesn't exist");c=this.wrapper;for(var e=this.wrapper.firstChild;null!==e&&1!==e.nodeType;)e=e.nextSibling;c.inner=e;f=this.options;b=this.wrapper;this._init(this)};s.prototype={destroy:function(){this._removeStyles();
p(b,"closed");p(b,"opened");b.removeAttribute("style");b.removeAttribute("aria-hidden");q=b=null;k(g,"load",this,!1);k(g,"resize",this,!1);k(e,"mousedown",this,!1);k(e,"touchstart",this,!1);k(e,"touchend",this,!1);k(e,"keyup",this,!1);k(e,"click",this,!1);f.customToggle?e.removeAttribute("aria-hidden"):e.parentNode.removeChild(e)},toggle:function(){r?(p(b,"opened"),n(b,"closed"),l(b,{"aria-hidden":"true"}),f.animate?setTimeout(function(){b.style.position="absolute"},f.transition+10):b.style.position=
"absolute",r=!1,f.close()):(p(b,"closed"),n(b,"opened"),b.style.position=f.openPos,l(b,{"aria-hidden":"false"}),r=!0,f.open())},handleEvent:function(a){a=a||g.event;switch(a.type){case "mousedown":this._onmousedown(a);break;case "touchstart":this._ontouchstart(a);break;case "touchend":this._ontouchend(a);break;case "keyup":this._onkeyup(a);break;case "click":this._onclick(a);break;case "load":this._transitions(a);this._resize(a);break;case "resize":this._resize(a)}},_init:function(){n(b,"closed");
this._createToggle();j(g,"load",this,!1);j(g,"resize",this,!1);j(e,"mousedown",this,!1);j(e,"touchstart",this,!1);j(e,"touchend",this,!1);j(e,"keyup",this,!1);j(e,"click",this,!1)},_createStyles:function(){m.parentNode||v.appendChild(m)},_removeStyles:function(){m.parentNode&&m.parentNode.removeChild(m)},_createToggle:function(){if(f.customToggle){var a=f.customToggle.replace("#","");if(h.getElementById(a))e=h.getElementById(a);else throw Error("The custom nav toggle you are trying to select doesn't exist");
}else a=h.createElement("a"),a.innerHTML=f.label,l(a,{href:"#",id:"nav-toggle"}),"after"===f.insert?b.parentNode.insertBefore(a,b.nextSibling):b.parentNode.insertBefore(a,b),e=h.getElementById("nav-toggle")},_preventDefault:function(a){a.preventDefault?(a.preventDefault(),a.stopPropagation()):a.returnValue=!1},_onmousedown:function(a){var b=a||g.event;3===b.which||2===b.button||(this._preventDefault(a),this.toggle(a))},_ontouchstart:function(a){e.onmousedown=null;this._preventDefault(a);this.toggle(a)},
_ontouchend:function(){var a=this;b.addEventListener("click",a._preventDefault,!0);setTimeout(function(){b.removeEventListener("click",a._preventDefault,!0)},f.transition)},_onkeyup:function(a){13===(a||g.event).keyCode&&this.toggle(a)},_onclick:function(a){this._preventDefault(a)},_transitions:function(){if(f.animate){var a=b.style,d="max-height "+f.transition+"ms";a.WebkitTransition=d;a.MozTransition=d;a.OTransition=d;a.transition=d}},_calcHeight:function(){var a="#"+this.wrapperEl+".opened{max-height:"+
b.inner.offsetHeight+"px}";t&&(m.innerHTML=a)},_resize:function(){"none"!==g.getComputedStyle(e,null).getPropertyValue("display")?(l(e,{"aria-hidden":"false"}),b.className.match(/(^|\s)closed(\s|$)/)&&(l(b,{"aria-hidden":"true"}),b.style.position="absolute"),this._createStyles(),this._calcHeight()):(l(e,{"aria-hidden":"true"}),l(b,{"aria-hidden":"false"}),b.style.position=f.openPos,this._removeStyles());f.init()}};var q;return function(a,b){q||(q=new s(a,b));return q}}(window,document);


/*
jQuery Hotkeys Plugin
Copyright 2010, John Resig
Dual licensed under the MIT or GPL Version 2 licenses.

Based upon the plugin by Tzury Bar Yochay:
http://github.com/tzuryby/hotkeys
Original idea by:
Binny V A, http://www.openjs.com/scripts/events/keyboard_shortcuts/
*/

(function(jQuery){jQuery.hotkeys={version:"0.8",specialKeys:{8:"backspace",9:"tab",10:"return",13:"return",16:"shift",17:"ctrl",18:"alt",19:"pause",20:"capslock",27:"esc",32:"space",33:"pageup",34:"pagedown",35:"end",36:"home",37:"left",38:"up",39:"right",40:"down",45:"insert",46:"del",96:"0",97:"1",98:"2",99:"3",100:"4",101:"5",102:"6",103:"7",104:"8",105:"9",106:"*",107:"+",109:"-",110:".",111:"/",112:"f1",113:"f2",114:"f3",115:"f4",116:"f5",117:"f6",118:"f7",119:"f8",120:"f9",121:"f10",122:"f11",123:"f12",144:"numlock",145:"scroll",186:";",191:"/",220:"\\",222:"'",224:"meta"},shiftNums:{"`":"~","1":"!","2":"@","3":"#","4":"$","5":"%","6":"^","7":"&","8":"*","9":"(","0":")","-":"_","=":"+",";":": ","'":"\"",",":"<",".":">","/":"?","\\":"|"}};function keyHandler(handleObj){if(typeof handleObj.data==="string"){handleObj.data={keys:handleObj.data};}
if(!handleObj.data||!handleObj.data.keys||typeof handleObj.data.keys!=="string"){return;}
var origHandler=handleObj.handler,keys=handleObj.data.keys.toLowerCase().split(" "),textAcceptingInputTypes=["text","password","number","email","url","range","date","month","week","time","datetime","datetime-local","search","color","tel"];handleObj.handler=function(event){if(this!==event.target&&(/textarea|select/i.test(event.target.nodeName)||jQuery.inArray(event.target.type,textAcceptingInputTypes)>-1)){return;}
var special=jQuery.hotkeys.specialKeys[event.keyCode],character=event.type==="keypress"&&String.fromCharCode(event.which).toLowerCase(),modif="",possible={};if(event.altKey&&special!=="alt"){modif+="alt+";}
if(event.ctrlKey&&special!=="ctrl"){modif+="ctrl+";}
if(event.metaKey&&!event.ctrlKey&&special!=="meta"){modif+="meta+";}
if(event.shiftKey&&special!=="shift"){modif+="shift+";}
if(special){possible[modif+special]=true;}
if(character){possible[modif+character]=true;possible[modif+jQuery.hotkeys.shiftNums[character]]=true;if(modif==="shift+"){possible[jQuery.hotkeys.shiftNums[character]]=true;}}
for(var i=0,l=keys.length;i<l;i++){if(possible[keys[i]]){return origHandler.apply(this,arguments);}}};}
jQuery.each(["keydown","keyup","keypress"],function(){jQuery.event.special[this]={add:keyHandler};});})(this.jQuery);