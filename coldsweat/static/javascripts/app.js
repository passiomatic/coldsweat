// Put app scripts here
    
$(document).ready(function() {
    "use strict";

    var flash_fragment = $('<div class="flash"><i class="fa fa-3x"></i><div class="message">&nbsp;</div></div>')
    var alert_fragment = $('<div class="alert alert--error" style="display:none"></div>')
    var modal_fragment = $('<div role="dialog" class="modal fade hide"></div>')
    var loading_fragment = $('<div class="loading"><i class="fa fa-spinner fa-spin"></i> Loading&hellip;</div>')
    //var loading_favicon_fragment = $('<i class="favicon fa fa-spinner fa-spin"></i>')

    $(document).ajaxError(function(event, jqXHR, settings, exception) {
        alert('Oops! An error occurred while processing your request: ' + exception)
    });

    function flash(icon, message) {
        var fragment = flash_fragment.clone()
        fragment.find('i').addClass('fa-' + icon)
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
    
    function mark(id, status) {
        $.ajax(endpoint('/entries/') + id, {
            type: 'POST', 
            data: 'mark&as=' + status
        })        
    }    

    function toggleRead(event) {
        var icon = $(event.target)
        var li = icon.parents('li').first()
        li.toggleClass('status-read');                
        var status = 'read'
        if(li.hasClass('status-read')) {
            //if(event.type != 'click') { flash('circle-o', 'Read'); }
            flash('circle-o', 'Read');
            icon.removeClass('icon-unread').addClass('icon-read')                            
        }else{
            status = 'unread'  
            flash('circle', 'Unread');
            icon.removeClass('icon-read').addClass('icon-unread')                
        } 
        mark(li.data('entry'), status)
    }

    function toggleSaved(event) {
        var icon = $(event.target)
        var li = icon.parents('li').first()
        li.toggleClass('status-saved')                
        var status = 'saved'
        if(li.hasClass('status-saved')) {
            flash('star', 'Saved');
            icon.removeClass('icon-unsaved').addClass('icon-saved')                            
        } else {
            status = 'unsaved'
            flash('star-o', 'Unsaved');
            icon.removeClass('icon-saved').addClass('icon-unsaved')                            
        }
        mark(li.data('entry'),  status);
    }

    function open(pathname) {       
        return function() {
            window.location.assign(endpoint(pathname))            
        } 
    }
    
    function moveTo(direction) {        
        return function (event) {            
            // Each() deals with empty set too
            $(direction == 'next' ? '.view a[rel=next]' : '.view a[rel=prev]').each(function(){                
                window.location.assign(($(this).attr('href')))
            })
        }
    }

    function bindKeyboardShortcuts() {
        var events = {
            '1': open('entries?filter=unread'),
            '2': open('entries?filter=saved'),
            '3': open('entries?filter=all'),
            '4': open('groups'),
            '5': open('feeds'), 
            //'a': function() { $('nav .add-trigger').click() },
            'm': function() { $('.entry.expanded .read-trigger').click() },
            's': function() { $('.entry.expanded .save-trigger').click() },
            //'j': moveTo('prev'),
            'k': moveTo('next'),
            // Bypass pop-up blocking mechanism (unfortunately a referrer URL is sent)
            'v': function(event) { event.preventDefault(); $('.entry.expanded .content a.btn-visit').each(function(){ window.open($(this).attr('href'),'_blank') }) }
        }
    
        for (var key in events) {      
            $(document).bind('keypress', key, events[key])  
        }
    }
    
    function setup() {               
        bindKeyboardShortcuts();

        // Setup popovers content using HTML
        //   from a given DOM element
        $('.popover-trigger').one('click', function(event) {
            event.preventDefault()
            var $this = $(this)
            var template = $this.attr('href')
            $this.popover({
                html: true, 
                placement: 'bottom', 
                content: $(template).html()
            })               
            $this.popover('show')
        }).one('shown', function(event) {
            var $this = $(this)
            var $popover = $this.data('popover').$tip
            $popover.delegate('a', 'click', function (event) {
                $this.popover('hide');
            });
        })
        
        // Setup tooltips with global options
        $('a[data-toggle="tooltip"]').tooltip({delay: 500})
        
        // Remote modals
        $(document).on('click', '[data-remote-modal]', function(event) { 
            event.preventDefault()
            var fragment = modal_fragment.clone() 
            fragment.attr('id', $(this).data('remote-modal'))
            fragment.load($(this).attr('href'), function(response, status, jqXHR) {
                fragment.html(response)
                fragment.on('hidden', function(event) {
                    fragment.remove() // Remove from DOM
                })
                fragment.modal('show')
            });            
        })
      
        $(document).on('submit', '.modal form[data-ajax-post]', function(event) { 
            event.preventDefault()
            var form = $(event.target)
            var serializedData = form.serialize()
            form.find('.modal-footer').html(loading_fragment)
            $.ajax(form.attr('action'), { 
                type: form.attr('method'), 
                data: serializedData}).done(function(data, textStatus, jqXHR) {                               
                    // Replace form with response only if HTML (it could be script)
                    var contentType = jqXHR.getResponseHeader('content-type') || '';
                    if (contentType.indexOf('text/html') == 0) {
                        form.replaceWith(data)                   
                    }
            })       
        })

        // 'More...' link
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

        // Mark entry as read, saved etc.
        $(document).on('click', '.view .read-trigger', function(event) { toggleRead(event) })
        $(document).on('click', '.view .save-trigger', function(event) { toggleSaved(event) })

        // Profile form 
        $(document).on('click', '#show-password-trigger', function(event) {
            event.preventDefault()
            var $password = $('#password_')
            if ($password.prop('type') == 'password') {
                $(this).text('Hide')
                $password.prop('type', 'text')    
            } else {
                $(this).text('Show')
                $password.prop('type', 'password')
            }
        })
    }
    
    setup();
    
});


