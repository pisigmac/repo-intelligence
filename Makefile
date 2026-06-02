.PHONY: build up down logs test seed clean proto

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down -v

logs:
	docker-compose logs -f

test:
	pytest services/*/tests/ -v

seed:
	bash scripts/seed-data.sh

clean:
	docker-compose down -v
	docker system prune -f

proto:
	python -m grpc_tools.protoc -Iapi/grpc --python_out=libs/models --grpc_python_out=libs/models api/grpc/*.proto
