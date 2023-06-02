all: run

# Env. Setup 

venv:
	python3 -m venv .venv

install-deps:
	python -m pip install -r requirements.txt 

install-package:
	pip install -e .  
	
build-css:
	npm run build-css

watch-css:
	npm run watch-css

setup:
	flask --app coldsweat --debug setup
	flask --app coldsweat --debug import subscriptions.opml

run:
	flask --app coldsweat run --debug

fetch:
	flask --app coldsweat --debug fetch

# Tests

# make-test-db:
# 	export FLASK_APP=coldsweat
# 	flask setup alice@example.com -p secret-password -n "Alice Cooper"
# 	flask import tests/subscriptions.opml alice@example.com

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
	sqlite3 instance/coldsweat.db