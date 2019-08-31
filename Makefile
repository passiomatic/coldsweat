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


docker-build:
	docker build -t $(ORG)/$(IMG):$(TAG) -f docker/Dockerfile .

docker-run:
	docker run -p 9001:9001 -v $(CWD)/data:/var/lib/coldsweat/db $(ORG)/$(IMG):$(TAG)
