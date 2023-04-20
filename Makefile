all: clean-local build run
clean-local:
	cargo clean

build:
	docker-compose build

run:
	docker-compose up

install: build
	docker-compose up -d