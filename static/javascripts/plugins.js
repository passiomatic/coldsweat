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



