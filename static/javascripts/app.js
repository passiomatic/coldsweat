// Put app scripts here
    
$(document).ready(function() {
    "use strict";

    var scroll_options = { zIndex: 1 };
    var flash_fragment = $('<div class="flash"><i class="icon-star icon-4x"></i><div class="message">Starred</div></div>');
    var alert_fragment = $('<div class="alert alert--error"></div>');
    var loading_fragment = $('<div class="loading"><i class="icon-spinner icon-spin"></i> Loading&hellip;</div>');
    var panel = $('.panel');
    
/*
    $(window).resize(function(e) {
        // Adjust panel-1 height to viewport size. minues the .panel-title total height
        var height = $(window).height() - $(panel[1]).find('.panel-title').outerHeight();
        $(panel[1]).find('.viewport').css('height', height)
    });
*/
    
    $(document).ajaxError(function(event, jqxhr, settings, exception) {
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

    function flash(icon, message) {
            //flash_fragment.find('i').addClass(icon)
            //flash_fragment.find('.message').text(message)
            $(document.body).append(flash_fragment);
            flash_fragment.show().animate({'opacity': 'hide'}, 'slow', function() { flash_fragment.remove() } )         
    }

    function endpoint(pathname) {
        var segments = [
            window.applicationURL,
            pathname
        ];
                          
        return segments.join('');
    }
    
    function findCurrent() { return panel.find('li.current'); }
    
    // @@TODO: merge and rename in current()
    function setCurrent(el) {
        var current = findCurrent();
        if(current !== el) {
            current.toggleClass('current');        
            el.toggleClass('current');
        }        
        // flash('At top')
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
            var target = $(event.target);
            var c = target.parents('li').first(); 
            setCurrent(c);

            //console.log(target);
        }
                
        var article = $(c).find('article');
        // Already open?
        if(!article.is(":visible")) {
            // Loader            
            //article.html(loading_fragment);
            
            var url = $(c).find('h3 a').attr('href');
            $.ajax(endpoint(url), 
                {dataType: 'html', type:'GET'}).done(function(data) {
                article.html(data);
                article.slideDown(200);
            })        
            c.addClass('status-read')
            mark(c, 'read');            
        } else {
            article.slideUp(100);
        }
            
    }
    
    function loadListing(filter) {
        panel.empty().prepend(loading_fragment);

        $.ajax(endpoint(filter),         
            {dataType: 'html', type:'GET'}).done(function(data) {            
                panel.html(data);

                $(document).on('click', '.panel h3 a', function(event) { event.preventDefault(); openEntry(event); })                
                
                // Load more
                var li_more = panel.find('li.more');
                var form = li_more.find('form');
                form.on('submit', function(event) { 
                    event.preventDefault();
                    li_more.html(loading_fragment);
                    $.ajax(endpoint(form.attr('action')), 
                        {dataType: 'html', type:'GET'}).done(function(data) {            
                           li_more.replaceWith(data);
                    })       
                })
                
        })       
    }

    function moveTo(direction) {        
        return function (event) {
            var c = findCurrent()            
            if(direction=='next') {
                var el = c.next('li')        
            } else {
                var el = c.prev('li')
            }

            // Check if on top or on bottom of the list            
            if(el.length) {
                c.toggleClass('current');        
                el.toggleClass('current');
                $(document.body).animate({'scrollTop': el.position().top}, 100);
            }
            
        }
    }

    function addSubscription() {
        $('#modal-add-subscription').modal('show');
    }
    
/*
    function showKeyboardShortcuts() {
        $('#modal-keyboard-shortcuts').modal('show');
    }
*/

    function bindKeyboardShortcuts() {
        var events = {
            'o': openEntry,
            'a': addSubscription,
            //'?': showKeyboardShortcuts,
            'm': toggleRead,
            's': toggleSaved,
            'j': moveTo('prev'),
            'k': moveTo('next')
        }
    
        for (var key in events) {      
            $(document).bind('keypress', key, events[key])  
        }
    }
    
    function setup() {               
        var filter = window.location.search;
        if(!filter) {
            filter = '/ajax/entries/?unread'; // Default
        }    
        //console.log(filter);        
        loadListing(filter);        
        bindKeyboardShortcuts();
        
        $('nav').find('.filter a').on('click', function(event) {
            event.preventDefault();    
            var filter = $(this).attr('href');
            loadListing(filter);
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
