all: run

# Env. Setup 

venv:
	python3 -m venv .venv

install-deps:
	python -m pip install -r requirements.txt 

build-css:
	npm run build-css

watch-css:
	npm run watch-css

run:
	flask --app coldsweat/app.py run --debug

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
	rm -rf dist/ build/ .parcel-cache/

# Database 

sql:
	sqlite3 data/coldsweat.db