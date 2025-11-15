.PHONY: help dev prod build stop logs shell clean db-shell

help: ## Show help
	@echo 'Available commands:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

dev: ## Start development server
	docker-compose up --build

prod: ## Start production with nginx
	docker-compose --profile production up --build -d

build: ## Build images
	docker-compose build

stop: ## Stop services
	docker-compose down

logs: ## Show logs
	docker-compose logs -f

shell: ## Open shell in container
	docker-compose exec web bash

db-shell: ## Open PostgreSQL shell
	docker-compose exec db psql -U horilla_user -d horilla_db

clean: ## Clean up
	docker-compose down -v
	docker system prune -f
