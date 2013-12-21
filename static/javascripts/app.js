// Put app scripts here
    
$(document).ready(function() {
    "use strict";

    var flash_fragment = $('<div class="flash"><i class="fa fa-4x"></i><div class="message">&nbsp;</div></div>')
    var alert_fragment = $('<div class="alert alert--error style="display:none"></div>')
    var modal_fragment = $('<div role="dialog" class="modal fade hide"></div>')
    var loading_fragment = $('<div class="loading"><i class="fa fa-spinner fa-spin"></i> Loading&hellip;</div>')
    //var loading_favicon_fragment = $('<i class="favicon fa fa-spinner fa-spin"></i>')

    var panel = $('.panel')
    
    $(document).ajaxError(function(event, jqxhr, settings, exception) {
        alert('Oops! An error occurred while processing your request: ' + exception)
    });

    function flash(icon, message) {
        var fragment = flash_fragment.clone()
        fragment.find('i').addClass('fa fa-' + icon)
        fragment.find('.message').text(message)
        $(document.body).append(fragment);
        fragment.show().animate({'opacity': 'hide'}, 'slow', function() { fragment.remove() } )         
    }
    
    function alert(message) {
        alert_fragment.text(message)
        $(document.body).prepend(alert_fragment);
        alert_fragment.slideDown('fast')
    }    

    function endpoint(pathname) {
        var segments = [
            window.applicationURL,
            pathname
        ]
                          
        return segments.join('')
    }
    
    function findCurrent() { return panel.find('li.current') }
    
    // @@TODO: merge and rename in current()
    function setCurrent(el) {
        var current = findCurrent()
        if(current !== el) {
            current.toggleClass('current')
            el.toggleClass('current')
        }        
        return current;
    }

    function mark(el, status) {
        $.ajax(endpoint('/entries/') + el.data('id'), {
            type: 'POST', 
            data: 'mark&as=' + status
        })        
    }    

    function toggleRead(event) {
        var el = findCurrent()
        el.toggleClass('status-read');                
        mark(el, el.hasClass('status-read') ? 'read' : 'unread')
    }

    function toggleSaved(event) {
        var status = 'unsaved'
        var el = findCurrent()
        el.toggleClass('status-saved');                
        if(el.hasClass('status-saved')) {
            flash('star', 'Saved')
            status = 'saved'
        } else {
            flash('star-o', 'Unsaved')
        }
        mark(el,  status);
    }

    function openEntry(event) {        
        var c = findCurrent()
        var url = c.find('h3 a').attr('href');
        window.location.assign(url)
    }
    
    function list(pathname) {       
        return function() {
            var url = endpoint(pathname);
            window.location.assign(url)            
        } 
    }
    
/*
    function loadListing(url) {
        panel.empty().prepend(loading_fragment);

        $.ajax(url,         
            {dataType: 'html', type:'GET'}).done(function(data) {            
                panel.html(data);
        })       
    }
*/

    function moveTo(direction) {        
        return function (event) {
            var c = findCurrent()            
            var scrollToTop = false;
            if(direction=='next') {
                var el = c.next('li')
            } else {
                var el = c.prev('li')
                var scrollToTop = true;
            }

            // Check if on top or on bottom of the list            
            if(el.length) {
                c.toggleClass('current');        
                el.toggleClass('current');
                $(document.body).animate({'scrollTop': el.position().top}, 100);
            } else if(scrollToTop) {
                $(document.body).animate({'scrollTop': 0}, 500);                
            }
            
        }
    }

/*
    function addSubscription() {
        $('#modal-add-subscription').modal();
    }
*/
    
/*
    function showKeyboardShortcuts() {
        $('#modal-keyboard-shortcuts').modal('show');
    }
*/

    function bindKeyboardShortcuts() {
        var events = {
            '1': list('/entries/?unread'),
            '2': list('/entries/?saved'),
            '3': list('/entries/?all'),
            '4': list('/feeds/'),
            'o': openEntry,
            //'a': addSubscription,
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

        $('.nav-trigger').hover(
            // in
            function(event) {
                // Slight delay
                setTimeout(function() { 
                    $('nav').addClass('open') 
                }, 100)
            }, 
            // out
            function(event) {}
        )

        $('nav').hover(
            // in
            function(event) {}, 
            // out
            function(event) {
                $(this).removeClass('open')
            }
        )

        // Remote modals
        $(document).on('click', '[data-remote-modal]', function(event) { 
            event.preventDefault()
            var fragment = modal_fragment.clone() 
            fragment.attr('id', $(this).data('remote-modal'))
            fragment.load($(this).attr('href'), function(response, status, xhr) {
                fragment.html(response)
                fragment.on('hidden', function(event) {
                    fragment.remove() // Remove from DOM
                })
                fragment.modal('show')
            });            
        })

        $(document).on('submit', '.modal form[method=POST]', function(event) { 
            event.preventDefault()
            var form = $(event.target)
            var serializedData = form.serialize()
            form.find('.modal-footer').hide()
            form.find('.modal-body').html(loading_fragment)
            $.ajax(form.attr('action'), 
                {dataType: 'html', type:form.attr('method'), data: serializedData}).done(function(data) {            
                   form.replaceWith(data)                   
            })       
        })

        // 'Load More...' link
        $(document).on('click', '.panel li.more a', function(event) { 
            event.preventDefault()            
            var parent = $(event.target).parents('li.more').first()
            parent.html(loading_fragment)
            $.ajax($(this).attr('href'), 
                {dataType: 'html', type:'GET'}).done(function(data) {            
                   $(document.body).animate({'scrollTop': parent.position().top}, 500)                   
                   parent.replaceWith(data)
            })       
        })

    }
    
    setup();
    
});


