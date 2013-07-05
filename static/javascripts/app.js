$(document).ready(function() {
    // Put app scripts here.

    // Set up responsive nav
/*
	var navElement = "#navigation-toggle";
	var navigation;
	navigation = responsiveNav("#navigation-toggle");
	navigation._transitions();
	navigation._resize();
    
    
*/

    function current() {
        return $('.entries li.current'); 
    }

    var ajax_endpoint = '/coldsweat/index.cgi/ajax/'
    
    // Open/close
    $(document).bind('keypress', 'o', function(e) {
        current().click();
    });

    // Mark as read
    $(document).bind('keypress', 'm', function(e) {        
        //@@TODO: cache ? 
        $.ajax(ajax_endpoint + 'entries/' + current().attr('id'), {
            dataType: 'script',             
            type: 'POST', 
            data: 'mark&as=read'
        })
    });

    // Star/unstar
    $(document).bind('keypress', 's', function(e) {
        //@@TODO: cache ? 
        $.ajax(ajax_endpoint + 'entries/' + current().attr('data-id'), {
            dataType: 'script',             
            type: 'POST', 
            data: 'mark&as=saved'
        })
    });
    

    $(document).bind('keypress', 'j', function(e) {
        //e.preventDefault();                
        var c = current().toggleClass('current');        
        var new_c = c.prevAll('li').first().toggleClass('current');
        console.log(new_c.offset().top)
        
        $('body').scrollTop(new_c.offset().top + c.height());        

    });

    $(document).bind('keypress', 'k', function(e) {
        //e.preventDefault();                        
        var c = current().toggleClass('current');        
        new_c = c.nextAll('li').first().toggleClass('current');        
        console.log(new_c.offset().top)

        $('body').scrollTop(new_c.offset().top - c.height());
    });
    

    $('.entries li').click(function(e) {
        var entry = $(this);
        //@@TODO: cache ? 
        $.ajax(ajax_endpoint + 'entries/' + entry.attr('id'), {dataType: 'script', type:'GET'}) 
        
        $('article').css('marginTop', entry.offset().top);
        
        
    })

    $('.entries li a').click(function(e) {
        e.preventDefault();                                
        // But let event to bubbling up
    })
		
});
