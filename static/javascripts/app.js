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

/*
    function get_current_entry() {
        return $('.entries li.current').find('a'); 
    }
*/
    
    $(document).bind('keypress', 'o', function(e) {
        e.preventDefault();                
        
        var c = $('.entries li.current a');        
        c.click();

    });

    // Mark as read
    $(document).bind('keypress', 'm', function(e) {
        
        var c = $('.entries li.current').find('a'); 
        //var article = $('article');
        
/*         if (content.is(":hidden")) { */
        //@@TODO: cache ? 
        $.ajax('/coldsweat/index.cgi/ajax/entries/' + c.attr('data-id'), {
            dataType: 'script',             
            type: 'POST', 
            data: 'mark&as=read'
        })

    });

    // Star|Unstar
    $(document).bind('keypress', 's', function(e) {
        var c = $('.entries li.current').find('a'); 
        //var article = $('article');
        
/*         if (content.is(":hidden")) { */
        //@@TODO: cache ? 
        $.ajax('/coldsweat/index.cgi/ajax/entries/' + c.attr('data-id'), {
            dataType: 'script',             
            type: 'POST', 
            data: 'mark&as=saved'
        })
                

    });
    

    $(document).bind('keypress', 'j', function(e) {
        e.preventDefault();                

        var c = $('.entries li.current').toggleClass('current');        
        var new_c = c.prevAll('li').first().toggleClass('current');

        $('body').scrollTop(new_c.offset().top + c.height());        

    });

    $(document).bind('keypress', 'k', function(e) {
        e.preventDefault();                
        
        var c = $('.entries li.current').toggleClass('current');        
        new_c = c.nextAll('li').first().toggleClass('current');
        
        $('body').scrollTop(new_c.offset().top - c.height());
        
        //first().addClass('current')

        //console.log(current.next('dt').attr('data-entry-id'))

/*
        if(){
        } else {
        }
*/

    });
    

    $('.entries li a').click(function(e) {
        e.preventDefault();                
        
        var anchor = $(this);
        //var article = $('article');
        
/*         if (content.is(":hidden")) { */
        //@@TODO: cache ? 
        $.ajax('/coldsweat/index.cgi/ajax/entries/' + anchor.attr('data-id'), {dataType: 'script', type:'GET', success:function(data, textStatus){
        }})
/*
        } 
        else {
                //content.hide();
        }
*/
                
    })
		
});
