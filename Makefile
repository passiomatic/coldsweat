CSS_FILES=./coldsweat/static/stylesheets/all.scss:./coldsweat/static/stylesheets/all.css

all: update

# Env. Setup 

venv:
	python3 -m venv .venv

install-deps:
	python -m pip install -r requirements.txt 

update:
	sass -f -t compressed --update $(CSS_FILES)

watch:
	sass --watch $(CSS_FILES)

# Tests

test:
	python -m pytest

# Build Wheel/PyPI Support

install-build-deps:
	python -m pip install build twine

build: clean
	python -m build

check:
	twine check dist/* 

upload:
	twine upload dist/*

upload-test:
	twine upload -r testpypi dist/*

clean:
	rm -rf dist/ build/