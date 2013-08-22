// Put app scripts here
    
$(document).ready(function() {
    "use strict";

    var scroll_options = { zIndex: 1 };
    
    var flash_fragment = $('<div class="flash"><i class="icon-star icon-4x"></i><div>Starred</div></div>');
    var alert_fragment = $('<div class="alert alert--error"></div>');
    var loading_fragment = $('<div class="loading"><i class="icon-spinner icon-spin"></i> Loading&hellip;</div>');
    
    var panels = $('.panel')
    
    $(window).resize(function(e) {
        // Adjust panel-1 height to viewport size. minues the .panel-title total height
        var height = $(window).height() - $(panels[1]).find('.panel-title').outerHeight();
        $(panels[1]).find('.viewport').css('height', height)
    });
    
    $(document).ajaxError(function(event, jqxhr, settings, exception) {
        //console.log('AJAX call details: ' + settings.url
        alert_fragment.text('Oops! An error occurred while processing your request: ' + exception)
        $(document.body).prepend(alert_fragment)
    });

/*
    $(document.body).blur(function() {
        console.log('Lost focus');
    });

    $(document.body).focus(function() {
        console.log('Got focus');
    });
*/


    function endpoint(pathname) {
        var segments = [
            window.applicationURL,
            pathname
        ];
                          
        return segments.join('');
    }
    
    function findCurrent() { return $(panels[1]).find('li.current'); }
    
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
        $.ajax(endpoint('/ajax/entries/') + el.attr('id'), {
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
        var article = $(panels[2]).find('article');
        if(article.attr('id') != c.attr('id')) {
            // Loader            
            article.html(loading_fragment);
            
            $.ajax(endpoint('/ajax/entries/') + c.attr('id'), 
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
    
    function loadEntries(filter) {
        $(panels[1]).empty().prepend(loading_fragment);
        
        $.ajax(endpoint('/ajax/entries/') + filter, 
            {dataType: 'html', type:'GET'}).done(function(data) {            
                $(panels[1]).html(data);
                
                // Update layout and navigation                
                $(window).resize();
                $(panels[1]).find('.scrollable').makeScrollable();

                // Let event to bubbling up                
                $(panels[1]).find('li a').click(function(event) { event.preventDefault(); })                
                $(panels[1]).find('li').click(function(event) { openEntry(event); })
        })       
    }

    function goToEntry(direction) {        
        function _goToEntry(event) {
            var c = findCurrent()            
            if(direction=='next') {
                var el = c.next('li')        
            } else {
                var el = c.prev('li')
            }

            // Check if on top or on bottom of the list            
            if(el.length) {
                c.toggleClass('current');        
                el.toggleClass('current'); //.focus();
                // Adjust scolling position
                $('.scrollable').updateScrollPosition(el.position().top);
            }
            
        }
        return _goToEntry;
    }

    function bindKeyboardEvents() {
        var events = {
            'o': openEntry,
            'm': toggleRead,
            's': toggleSaved,
            'j': goToEntry('prev'),
            'k': goToEntry('next')
        }
    
        for (var key in events) {      
            $(document).bind('keypress', key, events[key])  
        }    
    }
    
    function setup() {               
        $(window).resize();
        $('.panel-fixed').scrollToFixed(scroll_options);                     

        loadEntries('?unread');
        bindKeyboardEvents();

        $(panels[0]).find('.filter a').click(function(event) {
            event.preventDefault();    
            var filter = $(this).attr('href');
            //console.log(filter);
            loadEntries(filter);
        });
        
    }
    
    setup();
    
});


/*
    $.fn.hasAttr = function(attr) { 
        var value = this.attr(attr); 
        return (value !== undefined) && (value !== false); 
    }; 
*/
