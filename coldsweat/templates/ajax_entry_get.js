var article = $('article');
article.find('h1').html(
    '{{entry.title}}'
);
article.find('hr').after(
    {{entry.content|js}}
);    
