// Put app scripts here
    
$(document).ready(function() {
    "use strict";

    var ajax_endpoint = window.location.pathname + '/ajax/';

    var flash_fragment = $('<div class="flash"><i class="icon-star icon-4x"></i><div>Starred</div></div>');
    var alert_fragment = $('<div class="alert alert--error"></div>');
    var loading_fragment = $('<div class="loading"><i class="icon-spinner icon-spin"></i> Loading&hellip;</div>');
    
    $(window).resize(function(e) {
        // Adjust panel-2 height to viewport size. minues the .panel-title total height
        var height = $(window).height() - $('.panel-2 .panel-title').outerHeight()
        $('.panel-2 .viewport').css('height', height)        
        //console.log('Resized viewport');
    });
    $(window).resize();
    
    $('#scrollbar1').tinyscrollbar();
    $('.panel-1').scrollToFixed({
        zIndex: 1
    });    
    $('.panel-2').scrollToFixed({
        zIndex: 1,
    });
         
    $(document).ajaxError(function(event, jqxhr, settings, exception) {
        alert_fragment.text('Oops! An error occurred while processing your request: ' + exception);
        $(document.body).prepend(alert_fragment);
    });

/*
    $(document.body).blur(function() {
        console.log('Lost focus');
    });

    $(document.body).focus(function() {
        console.log('Got focus');
    });
*/


    function findCurrent() { return $('.entries li.current'); }
    
    // @TODO: rename in current()
    function setCurrent(el) {
        var current = findCurrent();
        if(current !== el) {
            current.toggleClass('current');        
            el.toggleClass('current');
        }        
        return current;
    }

    function mark(el, status) {
        $.ajax(ajax_endpoint + 'entries/' + el.attr('id'), {
            type: 'POST', 
            data: 'mark&as=' + status
        })        
    }    

    function toggleRead(event) {
        var el = findCurrent();
        el.toggleClass('status-read');                
        mark(el, el.hasClass('status-read') ? 'read' : 'unread');
    }

    function toggleSaved(event) {
        var status = 'unsaved';
        var el = findCurrent();
        el.toggleClass('status-saved');                
        if(el.hasClass('status-saved')) {
            $(document.body).append(flash_fragment);
            flash_fragment.show().animate({'opacity': 'hide'}, 'slow', function() { flash_fragment.remove() } )         
            status = 'saved'
        }
        mark(el,  status);
    }

    function openEntry(event) {        
        if(event.type != "click") {
            var c = findCurrent();
        } else {
            // Find LI parent's clicked target
            var target = $(event.target);
            var c = (target.tagName == 'li') ? target : target.parents('li').first(); 
            setCurrent(c);
        }
                
        // Already open?
        var article = $('article');
        if(article.attr('id') != c.attr('id')) {
            // Loader            
            article.empty().prepend(loading_fragment);
            
            $.ajax(ajax_endpoint + 'entries/' + c.attr('id'), 
                {dataType: 'html', type:'GET'}).done(function(data) {                
                // Mark article element with current loaded entry
                article.attr('id', c.attr('id'));
                article.html(data);
            })        
            //c.addClass('status-read')
            //mark(c, 'read');            
        } else {
            //@@TODO Play a *thump* sound  
            $(document.body).animate({'scrollTop': '0'}, 400);                        
        }
            
    }

    function goToEntry(direction) {        
        function _goToEntry(event) {
            var c = findCurrent()            
            if(direction=='next') {
                var el = c.next('li')        
            } else {
                var el = c.prev('li')
            }

            // Check if on top or on bottom            
            if(el.length) {
                c.toggleClass('current');        
                el.toggleClass('current'); //.focus();
                // Adjust scolling position
                $('#scrollbar1').tinyscrollbar_update(el.position().top);
            }
            
        }
        return _goToEntry;
    }

    function bindKeyboardEvents() {
        var keyboard_events = {
            'o': openEntry,
            'm': toggleRead,
            's': toggleSaved,
            'j': goToEntry('prev'),
            'k': goToEntry('next')
        }
    
        for (var key in keyboard_events) {      
            $(document).bind('keypress', key, keyboard_events[key])  
        }    
    }
    

    $('.entries li a').click(function(event) {
        event.preventDefault();            
        // ...but let event to bubbling up
    })

    $('.entries li').click(function(event) {
        openEntry(event)
    })

    bindKeyboardEvents()
        
});


/*
    $.fn.hasAttr = function(attr) { 
        var value = this.attr(attr); 
        return (value !== undefined) && (value !== false); 
    }; 
*/
