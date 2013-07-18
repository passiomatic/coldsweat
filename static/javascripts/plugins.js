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



/*
 * Tiny Scrollbar
 * http://www.baijs.nl/tinyscrollbar/
 *
 * Dual licensed under the MIT or GPL Version 2 licenses.
 * http://www.opensource.org/licenses/mit-license.php
 * http://www.opensource.org/licenses/gpl-2.0.php
 *
 * Date: 13 / 08 / 2012
 * @version 1.81
 * @author Maarten Baijs
 *
 */
;( function( $ ) 
{
    $.tiny = $.tiny || { };

    $.tiny.scrollbar = {
        options: {
                axis         : 'y'    // vertical or horizontal scrollbar? ( x || y ).
            ,   wheel        : 40     // how many pixels must the mouswheel scroll at a time.
            ,   scroll       : true   // enable or disable the mousewheel.
            ,   lockscroll   : true   // return scrollwheel to browser if there is no more content.
            ,   size         : 'auto' // set the size of the scrollbar to auto or a fixed number.
            ,   sizethumb    : 'auto' // set the size of the thumb to auto or a fixed number.
            ,   invertscroll : false  // Enable mobile invert style scrolling
        }
    };

    $.fn.makeScrollable = function( params )
    {
        var options = $.extend( {}, $.tiny.scrollbar.options, params );
        
        this.each( function()
        { 
            $( this ).data('tsb', new Scrollbar( $( this ), options ) ); 
        });

        return this;
    };

    $.fn.updateScrollPosition = function(sScroll)
    {
        return $( this ).data( 'tsb' ).update( sScroll ); 
    };

    function Scrollbar( root, options )
    {
        var oSelf       = this
        ,   oWrapper    = root
        ,   oViewport   = { obj: $( '.viewport', root ) }
        ,   oContent    = { obj: $( '.overview', root ) }
        ,   oScrollbar  = { obj: $( '.scrollbar', root ) }
        ,   oTrack      = { obj: $( '.track', oScrollbar.obj ) }
        ,   oThumb      = { obj: $( '.thumb', oScrollbar.obj ) }
        ,   sAxis       = options.axis === 'x'
        ,   sDirection  = sAxis ? 'left' : 'top'
        ,   sSize       = sAxis ? 'Width' : 'Height'
        ,   iScroll     = 0
        ,   iPosition   = { start: 0, now: 0 }
        ,   iMouse      = {}
        ,   touchEvents = 'ontouchstart' in document.documentElement
        ;

        function initialize()
        {
            oSelf.update();
            setEvents();

            return oSelf;
        }

        this.update = function( sScroll )
        {
            oViewport[ options.axis ] = oViewport.obj[0][ 'offset'+ sSize ];
            oContent[ options.axis ]  = oContent.obj[0][ 'scroll'+ sSize ];
            oContent.ratio            = oViewport[ options.axis ] / oContent[ options.axis ];

            oScrollbar.obj.toggleClass( 'disable', oContent.ratio >= 1 );

            oTrack[ options.axis ] = options.size === 'auto' ? oViewport[ options.axis ] : options.size;
            oThumb[ options.axis ] = Math.min( oTrack[ options.axis ], Math.max( 0, ( options.sizethumb === 'auto' ? ( oTrack[ options.axis ] * oContent.ratio ) : options.sizethumb ) ) );
        
            oScrollbar.ratio = options.sizethumb === 'auto' ? ( oContent[ options.axis ] / oTrack[ options.axis ] ) : ( oContent[ options.axis ] - oViewport[ options.axis ] ) / ( oTrack[ options.axis ] - oThumb[ options.axis ] );
            
            iScroll = ( sScroll === 'relative' && oContent.ratio <= 1 ) ? Math.min( ( oContent[ options.axis ] - oViewport[ options.axis ] ), Math.max( 0, iScroll )) : 0;
            iScroll = ( sScroll === 'bottom' && oContent.ratio <= 1 ) ? ( oContent[ options.axis ] - oViewport[ options.axis ] ) : isNaN( parseInt( sScroll, 10 ) ) ? iScroll : parseInt( sScroll, 10 );
            
            setSize();
        };

        function setSize()
        {
            var sCssSize = sSize.toLowerCase();

            oThumb.obj.css( sDirection, iScroll / oScrollbar.ratio );
            oContent.obj.css( sDirection, -iScroll );
            //oContent.obj.animate({sDirection: -iScroll}, 'fast');    

            //console.log( sDirection + ' ' + -iScroll);
            
            
            iMouse.start = oThumb.obj.offset()[ sDirection ];
            oScrollbar.obj.css( sCssSize, oTrack[ options.axis ] );
            oTrack.obj.css( sCssSize, oTrack[ options.axis ] );
            oThumb.obj.css( sCssSize, oThumb[ options.axis ] );
        }

        function setEvents()
        {
            if( ! touchEvents )
            {
                oThumb.obj.bind( 'mousedown', start );
                oTrack.obj.bind( 'mouseup', drag );
            }
            else
            {
                oViewport.obj[0].ontouchstart = function( event )
                {   
                    if( 1 === event.touches.length )
                    {
                        start( event.touches[ 0 ] );
                        event.stopPropagation();
                    }
                };
            }

            if( options.scroll && window.addEventListener )
            {
                oWrapper[0].addEventListener( 'DOMMouseScroll', wheel, false );
                oWrapper[0].addEventListener( 'mousewheel', wheel, false );
                oWrapper[0].addEventListener( 'MozMousePixelScroll', function( event ){
                    event.preventDefault();
                }, false);
            }
            else if( options.scroll )
            {
                oWrapper[0].onmousewheel = wheel;
            }
        }

        function start( event )
        {
            $( "body" ).addClass( "noSelect" );

            var oThumbDir   = parseInt( oThumb.obj.css( sDirection ), 10 );
            iMouse.start    = sAxis ? event.pageX : event.pageY;
            iPosition.start = oThumbDir == 'auto' ? 0 : oThumbDir;
            
            if( ! touchEvents )
            {
                $( document ).bind( 'mousemove', drag );
                $( document ).bind( 'mouseup', end );
                oThumb.obj.bind( 'mouseup', end );
            }
            else
            {
                document.ontouchmove = function( event )
                {
                    event.preventDefault();
                    drag( event.touches[ 0 ] );
                };
                document.ontouchend = end;        
            }
        }

        function wheel( event )
        {
            if( oContent.ratio < 1 )
            {
                var oEvent = event || window.event
                ,   iDelta = oEvent.wheelDelta ? oEvent.wheelDelta / 120 : -oEvent.detail / 3
                ;

                iScroll -= iDelta * options.wheel;
                iScroll = Math.min( ( oContent[ options.axis ] - oViewport[ options.axis ] ), Math.max( 0, iScroll ));

                oThumb.obj.css( sDirection, iScroll / oScrollbar.ratio );
                oContent.obj.css( sDirection, -iScroll );

                if( options.lockscroll || ( iScroll !== ( oContent[ options.axis ] - oViewport[ options.axis ] ) && iScroll !== 0 ) )
                {
                    oEvent = $.event.fix( oEvent );
                    oEvent.preventDefault();
                }
            }
        }

        function drag( event )
        {
            if( oContent.ratio < 1 )
            {
                if( options.invertscroll && touchEvents )
                {
                    iPosition.now = Math.min( ( oTrack[ options.axis ] - oThumb[ options.axis ] ), Math.max( 0, ( iPosition.start + ( iMouse.start - ( sAxis ? event.pageX : event.pageY ) ))));
                }
                else
                {
                     iPosition.now = Math.min( ( oTrack[ options.axis ] - oThumb[ options.axis ] ), Math.max( 0, ( iPosition.start + ( ( sAxis ? event.pageX : event.pageY ) - iMouse.start))));
                }

                iScroll = iPosition.now * oScrollbar.ratio;
                oContent.obj.css( sDirection, -iScroll );
                oThumb.obj.css( sDirection, iPosition.now );
            }
        }
        
        function end()
        {
            $( "body" ).removeClass( "noSelect" );
            $( document ).unbind( 'mousemove', drag );
            $( document ).unbind( 'mouseup', end );
            oThumb.obj.unbind( 'mouseup', end );
            document.ontouchmove = document.ontouchend = null;
        }

        return initialize();
    }

}(jQuery));



/*
 * ScrollToFixed
 * https://github.com/bigspotteddog/ScrollToFixed
 */
 
(function(a){a.isScrollToFixed=function(b){return a(b).data("ScrollToFixed")!==undefined};a.ScrollToFixed=function(d,h){var k=this;k.$el=a(d);k.el=d;k.$el.data("ScrollToFixed",k);var c=false;var F=k.$el;var G;var D;var p;var C=0;var q=0;var i=-1;var e=-1;var t=null;var y;var f;function u(){F.trigger("preUnfixed.ScrollToFixed");j();F.trigger("unfixed.ScrollToFixed");e=-1;C=F.offset().top;q=F.offset().left;if(k.options.offsets){q+=(F.offset().left-F.position().left)}if(i==-1){i=q}G=F.css("position");c=true;if(k.options.bottom!=-1){F.trigger("preFixed.ScrollToFixed");w();F.trigger("fixed.ScrollToFixed")}}function m(){var H=k.options.limit;if(!H){return 0}if(typeof(H)==="function"){return H.apply(F)}return H}function o(){return G==="fixed"}function x(){return G==="absolute"}function g(){return !(o()||x())}function w(){if(!o()){t.css({display:F.css("display"),width:F.outerWidth(true),height:F.outerHeight(true),"float":F.css("float")});cssOptions={position:"fixed",top:k.options.bottom==-1?s():"",bottom:k.options.bottom==-1?"":k.options.bottom,"margin-left":"0px"};if(!k.options.dontSetWidth){cssOptions.width=F.width()}F.css(cssOptions);F.addClass("scroll-to-fixed-fixed");if(k.options.className){F.addClass(k.options.className)}G="fixed"}}function b(){var I=m();var H=q;if(k.options.removeOffsets){H=0;I=I-C}cssOptions={position:"absolute",top:I,left:H,"margin-left":"0px",bottom:""};if(!k.options.dontSetWidth){cssOptions.width=F.width()}F.css(cssOptions);G="absolute"}function j(){if(!g()){e=-1;t.css("display","none");F.css({width:"",position:D,left:"",top:p.top,"margin-left":""});F.removeClass("scroll-to-fixed-fixed");if(k.options.className){F.removeClass(k.options.className)}G=null}}function v(H){if(H!=e){F.css("left",q-H);e=H}}function s(){var H=k.options.marginTop;if(!H){return 0}if(typeof(H)==="function"){return H.apply(F)}return H}function z(){if(!a.isScrollToFixed(F)){return}var J=c;if(!c){u()}var H=a(window).scrollLeft();var K=a(window).scrollTop();var I=m();if(k.options.minWidth&&a(window).width()<k.options.minWidth){if(!g()||!J){n();F.trigger("preUnfixed.ScrollToFixed");j();F.trigger("unfixed.ScrollToFixed")}}else{if(k.options.bottom==-1){if(I>0&&K>=I-s()){if(!x()||!J){n();F.trigger("preAbsolute.ScrollToFixed");b();F.trigger("unfixed.ScrollToFixed")}}else{if(K>=C-s()){if(!o()||!J){n();F.trigger("preFixed.ScrollToFixed");w();e=-1;F.trigger("fixed.ScrollToFixed")}v(H)}else{if(!g()||!J){n();F.trigger("preUnfixed.ScrollToFixed");j();F.trigger("unfixed.ScrollToFixed")}}}}else{if(I>0){if(K+a(window).height()-F.outerHeight(true)>=I-(s()||-l())){if(o()){n();F.trigger("preUnfixed.ScrollToFixed");if(D==="absolute"){b()}else{j()}F.trigger("unfixed.ScrollToFixed")}}else{if(!o()){n();F.trigger("preFixed.ScrollToFixed");w()}v(H);F.trigger("fixed.ScrollToFixed")}}else{v(H)}}}}function l(){if(!k.options.bottom){return 0}return k.options.bottom}function n(){var H=F.css("position");if(H=="absolute"){F.trigger("postAbsolute.ScrollToFixed")}else{if(H=="fixed"){F.trigger("postFixed.ScrollToFixed")}else{F.trigger("postUnfixed.ScrollToFixed")}}}var B=function(H){if(F.is(":visible")){c=false;z()}};var E=function(H){z()};var A=function(){var I=document.body;if(document.createElement&&I&&I.appendChild&&I.removeChild){var K=document.createElement("div");if(!K.getBoundingClientRect){return null}K.innerHTML="x";K.style.cssText="position:fixed;top:100px;";I.appendChild(K);var L=I.style.height,M=I.scrollTop;I.style.height="3000px";I.scrollTop=500;var H=K.getBoundingClientRect().top;I.style.height=L;var J=(H===100);I.removeChild(K);I.scrollTop=M;return J}return null};var r=function(H){H=H||window.event;if(H.preventDefault){H.preventDefault()}H.returnValue=false};k.init=function(){k.options=a.extend({},a.ScrollToFixed.defaultOptions,h);k.$el.css("z-index",k.options.zIndex);t=a("<div />");G=F.css("position");D=F.css("position");p=a.extend({},F.offset());if(g()){k.$el.after(t)}a(window).bind("resize.ScrollToFixed",B);a(window).bind("scroll.ScrollToFixed",E);if(k.options.preFixed){F.bind("preFixed.ScrollToFixed",k.options.preFixed)}if(k.options.postFixed){F.bind("postFixed.ScrollToFixed",k.options.postFixed)}if(k.options.preUnfixed){F.bind("preUnfixed.ScrollToFixed",k.options.preUnfixed)}if(k.options.postUnfixed){F.bind("postUnfixed.ScrollToFixed",k.options.postUnfixed)}if(k.options.preAbsolute){F.bind("preAbsolute.ScrollToFixed",k.options.preAbsolute)}if(k.options.postAbsolute){F.bind("postAbsolute.ScrollToFixed",k.options.postAbsolute)}if(k.options.fixed){F.bind("fixed.ScrollToFixed",k.options.fixed)}if(k.options.unfixed){F.bind("unfixed.ScrollToFixed",k.options.unfixed)}if(k.options.spacerClass){t.addClass(k.options.spacerClass)}F.bind("resize.ScrollToFixed",function(){t.height(F.height())});F.bind("scroll.ScrollToFixed",function(){F.trigger("preUnfixed.ScrollToFixed");j();F.trigger("unfixed.ScrollToFixed");z()});F.bind("detach.ScrollToFixed",function(H){r(H);F.trigger("preUnfixed.ScrollToFixed");j();F.trigger("unfixed.ScrollToFixed");a(window).unbind("resize.ScrollToFixed",B);a(window).unbind("scroll.ScrollToFixed",E);F.unbind(".ScrollToFixed");k.$el.removeData("ScrollToFixed")});B()};k.init()};a.ScrollToFixed.defaultOptions={marginTop:0,limit:0,bottom:-1,zIndex:1000};a.fn.scrollToFixed=function(b){return this.each(function(){(new a.ScrollToFixed(this,b))})}})(jQuery);

