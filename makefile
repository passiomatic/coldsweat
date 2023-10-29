all: run-debug

# Env. Setup 

venv:
	python3 -m venv .venv

install-js-deps:
	npm ci

install-deps: install-js-deps
	python -m pip install -r requirements.txt 

install-package:
	pip install -e .  
	
build-assets:
	npm run build-assets

watch-assets:
	npm run watch-assets

setup:
	flask --app coldsweat setup alice@example.com -p password1234 -n "Alice Cooper"
	flask --app coldsweat import tests/sample-subscriptions.opml alice@example.com -f

run:
	flask --app coldsweat run

run-debug:
	flask --app coldsweat run --debug

fetch:
	flask --app coldsweat --debug fetch

shell:
	flask --app coldsweat shell

reset:
	rm ./instance/coldsweat.db

# Tests

create-test-data: export FLASK_DATABASE_URL=sqlite:///instance/coldsweat-test.db

create-test-data:
	rm -f ./instance/coldsweat-test.db
	flask --app coldsweat setup test@example.com -p secret-password -n "Test User"
	flask --app coldsweat import ./tests/test-subscriptions.xml test@example.com -f
	sqlite3 ./instance/coldsweat-test.db ".dump" > tests/test-data.sql

test:
	python -m pytest -s

# Build Wheel/PyPI Support

install-build-deps:
	python -m pip install build twine

build: clean build-assets
	python -m build

check:
	twine check dist/* 

upload:
	twine upload -u passiomatic dist/*

upload-test:
	twine upload -u passiomatic -r testpypi dist/*

clean:
	rm -rf dist/ build/ .parcel-cache/

# Test deploy servers

run-gunicorn:
	gunicorn -w 8 'coldsweat:create_app()' --bind 127.0.0.1:5000

run-waitress:
	waitress-serve --host 127.0.0.1 --port 5000 --threads=8 --call coldsweat:create_app

# Database 

sql:
	sqlite3 instance/coldsweat.db