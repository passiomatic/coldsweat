var article = $('article');
// Title and link to original entry
article.find('h1').html(
    '<a target="_blank" href="{{entry.link}}">{{entry.title}}</a>'
);
// Feed information
article.find('.meta').html(
    '<a target="_blank" href="{{entry.feed.alternate_link}}">{{entry.feed.title}}</a>'
);
// Content, at last
article.find('hr').after(
    {{entry.content|javascript}}
);    
