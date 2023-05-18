CSS_FILES=./static/stylesheets/all.scss:./static/stylesheets/all.css

all: update

test:
	python -m pytest

venv:
	python3 -m venv .venv

install-deps:
	python -m pip install -r requirements.txt 

update:
	sass -f -t compressed --update $(CSS_FILES)

watch:
	sass --watch $(CSS_FILES)

clean:
	rm -r ./.sass-cache