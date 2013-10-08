// Put app scripts here
    
$(document).ready(function() {
    "use strict";

    //var scroll_options = { zIndex: 1 };
    var flash_fragment = $('<div class="flash"><i class="icon-star icon-4x"></i><div class="message">Starred</div></div>');
    var alert_fragment = $('<div class="alert alert--error"></div>');
    var loading_fragment = $('<div class="loading"><i class="icon-spinner icon-spin"></i> Loading&hellip;</div>');
    var loading_favicon_fragment = $('<i class="favicon icon-spinner icon-spin"></i>');

    var panel = $('.panel');
    
    //var speeds = [200, 100];
    
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
        $.ajax(endpoint('/entries/') + el.attr('id'), {
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
        if(!article.is(":visible")) {
        
            // Close open entries
            panel.find('article').filter(':visible').slideUp(100);
            
            // Show spinner            
            var img = $(c).find('.favicon').replaceWith(loading_favicon_fragment);
            
            var url = $(c).find('h3 a').attr('href');
            $.ajax(url, {dataType: 'html', type:'GET'}).done(function(data) {
                article.html(data);
                $(c).find('h3 i').replaceWith(img);
                article.slideDown(200);
            })        
            
            // Mark as read if entry
            if($(c).hasClass('entry')) {
                c.addClass('status-read')
                mark(c, 'read');            
            }            
        } else {
            article.slideUp(100);
        }
            
    }
    
    function loadListing(url) {
        panel.empty().prepend(loading_fragment);

        $.ajax(url,         
            {dataType: 'html', type:'GET'}).done(function(data) {            
                panel.html(data);

                //$(document).on('click', '.panel h3 a', function(event) { event.preventDefault(); openEntry(event); })                
                
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
        bindKeyboardShortcuts();

        // Bind events
        $(document).on('click', '.panel h3 a', function(event) { event.preventDefault(); openEntry(event); })  

        // Load more
        //var li_more = panel.find('li.more');
        //var form = li_more.find('form');
        $(document).on('submit', '.panel li.more form', function(event) { 
            event.preventDefault();
            
            var parent = $(this).parents('li.more').first();
            parent.html(loading_fragment);
            $.ajax($(this).attr('action'), 
                {dataType: 'html', type:'GET'}).done(function(data) {            
                   parent.replaceWith(data);
                   //$(document.body).animate({'scrollTop': li_more.position().top}, 100);                   
            })       
        })


        var form = $(document).find('#modal-add-subscription form');
        form.on('submit', function(event) { 
            event.preventDefault();
            var serializedData = form.serialize();
            //console.log(serializedData);
            form.html(loading_fragment);
            $.ajax(form.attr('action'), 
                {dataType: 'html', type:form.attr('method'), data: serializedData}).done(function(data) {            
                   form.replaceWith(data);                   
            })       
        })

    }
    
    setup();
    
});


/*
    $.fn.hasAttr = function(attr) { 
        var value = this.attr(attr); 
        return (value !== undefined) && (value !== false); 
    }; 
*/
