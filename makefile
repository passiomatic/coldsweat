CSS_FILES=./static/stylesheets/all.scss:./static/stylesheets/all.css
CSS_FILES_IE8=./static/stylesheets/lte-ie8.scss:./static/stylesheets/lte-ie8.css

all: update updateie8

update:
	sass --sourcemap -f -t compressed --update $(CSS_FILES)

updateie8:
	sass --sourcemap -f -t compressed --update $(CSS_FILES_IE8)

watch:
	sass --sourcemap --watch $(CSS_FILES)

clean:
	rm -r ./.sass-cache
	
