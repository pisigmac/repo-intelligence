.PHONY: build up down logs test seed clean proto start stop restart status reset migrate wait health setup

start:
	bash scripts/start_all.sh

stop:
	bash scripts/stop_all.sh

restart:
	bash scripts/restart_all.sh

status:
	bash scripts/status_all.sh

reset:
	bash scripts/reset_all.sh

migrate:
	bash scripts/apply-migrations.sh

wait:
	bash scripts/wait-for-healthy.sh

health:
	bash scripts/health.sh

setup:
	bash scripts/setup.sh

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down -v

logs:
	docker-compose logs -f

test:
	bash scripts/test.sh

test-unit:
	bash scripts/test.sh --unit-only

test-parser:
	bash scripts/test.sh --parser-only

seed:
	bash scripts/seed-data.sh

clean:
	docker-compose down -v
	docker system prune -f

proto:
	python -m grpc_tools.protoc -Iapi/grpc --python_out=libs/models --grpc_python_out=libs/models api/grpc/*.proto
