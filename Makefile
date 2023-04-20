all: build run
build:
	docker-compose build

run:
	docker-compose up

install: build
	docker-compose up -d