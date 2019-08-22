CSS_FILES=./static/stylesheets/all.scss:./static/stylesheets/all.css

.PHONY: test

test:
	python -m pytest

coverage:
	python -m pytest -vv --cov=coldsweat tests

all: update

update:
	sass -f -t compressed --update $(CSS_FILES)

watch:
	sass --watch $(CSS_FILES)

clean:
	rm -r ./.sass-cache
