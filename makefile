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
	flask --app coldsweat setup coldsweat@example.com -p some-password
	flask --app coldsweat import subscriptions.opml coldsweat@example.com

run:
	flask --app coldsweat run --debug

fetch:
	flask --app coldsweat --debug fetch

# Tests

create-test-data: export DATABASE_URL=sqlite:///instance/coldsweat-test.db

create-test-data:
	rm -f ./instance/coldsweat-test.db
	flask --app coldsweat setup test@example.com -p secret-password -n "Test User"
	flask --app coldsweat import ./tests/subscriptions.xml test@example.com -f
	sqlite3 ./instance/coldsweat-test.db ".dump" > tests/test-data.sql

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