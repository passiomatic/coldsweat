CSS_FILES=./coldsweat/stylesheets/all.scss:./coldsweat/stylesheets/all.css

all: cssupdate

cssupdate:
	sass -f -t compact --update $(CSS_FILES)

csswatch:
	sass --watch $(CSS_FILES)

cssclean:
	rm -r ./.sass-cache
	
