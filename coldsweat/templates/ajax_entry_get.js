var article = $('article');
article.find('h1').html(
    '<a target="_blank" href="{{entry.link}}">{{entry.title}}</a>'
);
article.find('hr').after(
    {{entry.content|javascript}}
);    
