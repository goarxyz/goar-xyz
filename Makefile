COMPOSE ?= docker compose

.PHONY: init build up down restart logs status shell test check clean proot-build proot-app proot-serve proot-stop proot-status proot-shell

init:
	@test -f .env || cp .env.example .env
	@mkdir -p workspace/downloads workspace/uploads
	@echo "Created .env (if absent) and the local workspace. Add a provider configuration before submitting agent tasks."

build:
	$(COMPOSE) build --pull

up:
	$(COMPOSE) up -d --build
	@echo "GOAR OS is available at http://$${GOAR_BIND_ADDRESS:-127.0.0.1}:$${GOAR_PORT:-8080}/"

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f --tail=200 goar

status:
	$(COMPOSE) ps
	@curl --fail --silent --show-error http://$${GOAR_BIND_ADDRESS:-127.0.0.1}:$${GOAR_PORT:-8080}/health | python3 -m json.tool

shell:
	$(COMPOSE) exec goar sh

test:
	python3 -m compileall -q goar-production
	bash -n goar-proot proot/build-rootfs.sh proot/rootfs-overlay/usr/local/bin/goar-serve
	python3 -m unittest discover -s tests -v

proot-build:
	./goar-proot build

proot-app:
	./goar-proot app

proot-serve:
	./goar-proot serve

proot-stop:
	./goar-proot stop

proot-status:
	./goar-proot status

proot-shell:
	./goar-proot shell

check:
	$(COMPOSE) config --quiet
	python3 -m compileall -q goar-production

clean:
	$(COMPOSE) down --remove-orphans
