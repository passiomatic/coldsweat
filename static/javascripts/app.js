// Put app scripts here
    
$(document).ready(function() {
    "use strict";

    var flash_fragment = $('<div class="flash"><i class="icon-4x"></i><div class="message">&nbsp;</div></div>')
    var alert_fragment = $('<div class="alert alert--error style="display:none"></div>')
    var modal_fragment = $('<div role="dialog" class="modal fade hide"></div>')
    var loading_fragment = $('<div class="loading"><i class="icon-spinner icon-spin"></i> Loading&hellip;</div>')
    var loading_favicon_fragment = $('<i class="favicon icon-spinner icon-spin"></i>')

    var panel = $('.panel')
    
    $(document).ajaxError(function(event, jqxhr, settings, exception) {
        alert('Oops! An error occurred while processing your request: ' + exception)
    });

    function flash(icon, message) {
        var fragment = flash_fragment.clone()
        fragment.find('i').addClass('icon-' + icon)
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
            flash('star-empty', 'Unsaved')
        }
        mark(el,  status);
    }

    function openEntry(event) {        
        if(event.type != "click") {
            var c = findCurrent()
        } else {
            var target = $(event.target);
            var c = target.parents('li').first()
            setCurrent(c);
        }
                
        var article = c.find('article')
        if(!article.is(":visible")) {
        
            // Close open entries
            //panel.find('article').filter(':visible').slideUp(200);
            
            // Show spinner            
            var img = c.find('.favicon').replaceWith(loading_favicon_fragment);
            
            var url = c.find('h3 a').attr('href');
            $.ajax(url, {dataType: 'html', type:'GET'}).done(function(data) {
                article.html(data);
                $(c).find('h3 i').replaceWith(img);
                article.show(200);
                $(document.body).animate({'scrollTop': c.position().top}, 500);          
                setTimeout(function() {
                    //if($(c).hasClass('entry')) {
                    c.addClass('status-read')
                    mark(c, 'read');            
                    //}            
                }, 1500);
            })        
            
        } else {
            //article.slideUp(100);
            article.hide();

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
            'o': openEntry,
            //'a': addSubscription,
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
        //$('body').off('.data-api')        

        // Open entry on title click
        $(document).on('click', '.panel li.entry h3 a', function(event) { event.preventDefault(); openEntry(event) })  
/*
        $(document).on('hidden', '.modal', function (event) {
        })
*/
    
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

        // 'Load More...' button
        $(document).on('submit', '.panel li.more form', function(event) { 
            event.preventDefault()            
            var parent = $(event.target).parents('li.more').first()
            parent.html(loading_fragment)
            $.ajax($(this).attr('action'), 
                {dataType: 'html', type:'GET'}).done(function(data) {            
                   $(document.body).animate({'scrollTop': parent.position().top}, 500)                   
                   parent.replaceWith(data)
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
