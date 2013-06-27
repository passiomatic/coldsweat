CSS_FILES=./static/stylesheets/all.scss:./static/stylesheets/all.css

all: cssupdate

cssupdate:
	sass -f -t compact --update $(CSS_FILES)

csswatch:
	sass --watch $(CSS_FILES)

cssclean:
	rm -r ./.sass-cache
	
