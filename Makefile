CSS_FILES=./static/stylesheets/all.scss:./static/stylesheets/all.css

.PHONY: test coverage all watch clean docker-build docker-run save cp-to-server \
	import-on-server run-on-server disable-on-server

.DEFAULT_GOAL := help

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

PY ?= python3

help:
	@$(PY) -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)
test:  ## run the test suite with pytest
	python -m pytest

coverage:  ## run the tests and collect metrics
	python -m pytest -vv --cov=coldsweat tests

all: update

venv:
	python3 -m venv .venv

install-deps:
	python -m pip install -r requirements.txt 

update:  ## update css files from sass sources
	sass -f -t compressed --update $(CSS_FILES)

watch:  ## rebuild css on changes to sass sources
	sass --watch $(CSS_FILES)

clean:  ## remove sass cache
	rm -r ./.sass-cache


docker-build:  ## build a docker image
	docker build -t $(ORG)/$(IMG):$(TAG) -f docker/Dockerfile .

docker-run:  ## run the docker image locally
	docker run -it -p 9001:9001 -v $(CURDIR)/data:/var/lib/coldsweat/db $(ORG)/$(IMG):$(TAG)

save:  ## saves the image to a localfile
	sudo docker save $(ORG)/$(IMG):$(TAG) > $(ORG).$(IMG).$(TAG).img


cp-to-server:  ## upload the image to a server
	scp $(ORG).$(IMG).$(TAG).img $(SERVER):~/


import-on-server:  ## imports the image on the serve
	ssh -t $(SERVER) "echo $(SUDOPASSWORD) | sudo -S docker load --input  $(ORG).$(IMG).$(TAG).img"


run-on-server:  ## runs the docker image on a remote server
	ssh -t $(SERVER) "echo $(SUDOPASSWORD) | sudo -S docker run --name $(CONTAINERNAME) \
		-d --restart always
		-v $(BASEDIR):/var/lib/tinycms/db \
		-p $(HOST):9001:9001 $(ORG)/$(IMG):$(TAG)"

disable-on-server:  ## stops the container on a remote server
	ssh -t $(SERVER) "echo $(SUDOPASSWORD) | sudo -S docker rm --force $(CONTAINERNAME)"
