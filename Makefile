.PHONY: help install build up down logs test lint format clean load-test docs

help:
	@echo "Ethera - Inventory Management System"
	@echo "===================================="
	@echo ""
	@echo "Development Commands:"
	@echo "  make install       - Install dependencies"
	@echo "  make build         - Build Docker images"
	@echo "  make up            - Start all services (Docker Compose)"
	@echo "  make down          - Stop all services"
	@echo "  make logs           - Show logs from all services"
	@echo "  make restart       - Restart services"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test          - Run unit tests"
	@echo "  make load-test-light   - Light load test (100 users)"
	@echo "  make load-test-heavy   - Heavy load test (1000 users)"
	@echo "  make lint          - Run linting checks"
	@echo "  make format        - Format code"
	@echo ""
	@echo "Database:"
	@echo "  make migrate       - Run database migrations"
	@echo "  make db-reset      - Reset database (WARNING: deletes all data)"
	@echo "  make db-backup     - Backup database"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs          - Show API docs (http://localhost:8000/docs)"
	@echo ""

install:
	pip install -r backend/requirements.txt
	npm install --prefix frontend
	pip install locust pytest pytest-asyncio

build:
	docker compose build

up:
	docker compose up -d
	@echo "✓ Services started"
	@echo "  Frontend: http://localhost:3000"
	@echo "  Backend: http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

down:
	docker compose down

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

restart:
	docker compose restart

test:
	docker compose exec backend pytest -v

test-coverage:
	docker compose exec backend pytest --cov=app --cov-report=html

lint:
	docker compose exec backend flake8 app --max-line-length=120
	docker compose exec backend black --check app

format:
	docker compose exec backend black app
	docker compose exec backend isort app

migrate:
	docker compose exec backend alembic upgrade head

db-reset:
	@echo "⚠️  WARNING: This will delete all data!"
	@read -p "Are you sure? (yes/no) " confirm && [ "$$confirm" = "yes" ] || exit 1
	docker compose exec backend python -c "from app.database import init_db; asyncio.run(init_db())"

db-backup:
	@mkdir -p backups
	docker compose exec -T db pg_dump -U postgres ethera > backups/backup-$$(date +%Y%m%d-%H%M%S).sql
	@echo "✓ Database backed up to backups/"

shell:
	docker compose exec backend python -c "import asyncio; asyncio.run(asyncio.sleep(0))" && docker compose exec backend bash

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	docker compose down -v
	@echo "✓ Cleaned up"

# Load Testing
load-test-light:
	locust -f tests/load_test.py --users=100 --spawn-rate=10 -H http://localhost:8000

load-test-moderate:
	locust -f tests/load_test.py --users=500 --spawn-rate=25 -H http://localhost:8000

load-test-heavy:
	locust -f tests/load_test.py --users=1000 --spawn-rate=50 -H http://localhost:8000

load-test-stress:
	locust -f tests/load_test.py --users=5000 --spawn-rate=100 -H http://localhost:8000

# Monitoring
check-health:
	curl -s http://localhost:8000/health | python -m json.tool

dashboard:
	curl -s http://localhost:8000/analytics/dashboard | python -m json.tool

# Documentation
docs:
	@echo "📚 API Documentation:"
	@echo "  Swagger UI: http://localhost:8000/docs"
	@echo "  ReDoc: http://localhost:8000/redoc"
	@echo ""
	@echo "📖 Guides:"
	@echo "  Optimization: See OPTIMIZATION_GUIDE.md"
	@echo "  Deployment: See DEPLOYMENT.md"
	@echo "  Summary: See OPTIMIZATION_SUMMARY.md"

# Deployment
deploy-backend:
	@echo "🚀 Deploying backend to Render..."
	@echo "  1. Push to GitHub (automatic deploy via render.yaml)"
	@echo "  2. Monitor at https://render.com"

deploy-frontend:
	@echo "🚀 Deploying frontend to Netlify..."
	netlify deploy --prod --dir=frontend/build

deploy-docker:
	docker build -t yourusername/ethera-backend:latest ./backend
	docker push yourusername/ethera-backend:latest
	@echo "✓ Image pushed to Docker Hub"

# Development workflow
dev: build up
	@echo "✓ Development environment ready"

dev-stop: down
	@echo "✓ Development environment stopped"

# Quick start
quickstart: build up install
	@sleep 5
	@echo ""
	@echo "✓ Ethera is running!"
	@echo "  Frontend: http://localhost:3000"
	@echo "  API: http://localhost:8000"
	@echo "  Docs: http://localhost:8000/docs"
	@echo ""
	@echo "Next steps:"
	@echo "  - Open http://localhost:3000 in browser"
	@echo "  - Create a product"
	@echo "  - Create a customer"
	@echo "  - Create an order"
	@echo ""
	@echo "Run 'make help' for more commands"
