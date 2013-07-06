$(document).ready(function() {
    "use strict";

    var flash_fragment = '<div class="flash"><i class="icon-star icon-4x"></i><div>Starred</div></div>';
      
    // Put app scripts here

    var ajax_endpoint = window.location.pathname + '/ajax/';
    // Adjust panel-2 height to viewport size. minues page-title total height
    var h = $(window).height() - $('.panel-2 .panel-title').outerHeight()
    $('.panel-2 .viewport').css('height', h)    
    $(window).resize(function(e) {
        var h = $(window).height() - $('.panel-2 .panel-title').outerHeight()
        $('.panel-2 .viewport').css('height', h)
    });

     $('#scrollbar1').tinyscrollbar();
     $('.panel-1').scrollToFixed();    
     $('.panel-2').scrollToFixed();
         

    function findCurrent() { return $('.entries li.current'); }

    function markAsRead() {
        var c = findCurrent();    
        c.toggleClass('status-read');    
    
        $.ajax(ajax_endpoint + 'entries/' + c.attr('id'), {
            dataType: 'script',             
            type: 'POST', 
            data: 'mark&as=read'
        })        
    }

    function markAsSaved() {
        var c = findCurrent();    
        c.toggleClass('status-saved');
        
        // Animate
        var flash = $(flash_fragment);
        $(document.body).append(flash);
        flash.animate({'opacity': 'hide'}, 'slow', function() { flash.remove() } ) 

        $.ajax(ajax_endpoint + 'entries/' + c.attr('id'), {
            dataType: 'html',             
            type: 'POST', 
            data: 'mark&as=saved'
        })        
    }

    function openEntry(e) {        
            var c = findCurrent();
        //@@TODO: check if already open
        $.ajax(ajax_endpoint + 'entries/' + c.attr('id'), {dataType: 'html', type:'GET'}).done(function(data) {
            $('article').html(data);
        })        

        if(e == undefined) {


        } else {
            var c = $(e.target);
        }
        
        
    }

    function goToEntry(direction) {        
        function _goToEntry(e) {
            var c = findCurrent()            
            //e.preventDefault();                
            if(direction=='next') {
                var el = c.next('li')        
            } else {
                var el = c.prev('li')
            }

            // Check if on top or on bottom            
            if(el.length) {
                c.toggleClass('current');        
                el.toggleClass('current');
                // Adjust scolling position
                $('#scrollbar1').tinyscrollbar_update(el.position().top);
            }
            
        }
        return _goToEntry;
    }
    
    function bindKeyboardEvents() {
        var keyboard_events = {
            'o': openEntry,
            'm': markAsRead,
            's': markAsSaved,
            'j': goToEntry('prev'),
            'k': goToEntry('next')
        }
    
        for (var key in keyboard_events) {      
            $(document).bind('keypress', key, keyboard_events[key])  
        }    
    }
    

    $('.entries li a').click(function(e) {
        e.preventDefault();            
        // But let event to bubbling up
    })

    $('.entries li').click(function(e) {
        openEntry(e)
    })

    bindKeyboardEvents()
        
});
