CSS_FILES=./static/stylesheets/all.scss:./static/stylesheets/all.css

all: update

update:
	sass --sourcemap -f -t compressed --update $(CSS_FILES)

watch:
	sass --sourcemap --watch $(CSS_FILES)

clean:
	rm -r ./.sass-cache
	
