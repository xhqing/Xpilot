.PHONY: install dev test lint clean build docker-build docker-run docker-shell dev-proxy dev-proxy-stop dev-proxy-restart dev-proxy-status dev-proxy-test dev-proxy-nodes dev-proxy-node dev-proxy-restart-node

# Install dependencies in editable mode
install:
	pip install -e ".[dev]"

# Install dev dependencies only
dev:
	pip install -e ".[dev]"

# Run tests
test:
	python -m pytest tests/ -v

# Run tests with coverage
test-cov:
	python -m pytest tests/ -v --cov=xray_pilot --cov-report=term-missing

# Lint code
lint:
	ruff check xray_pilot/ tests/

# Format code
fmt:
	ruff check xray_pilot/ tests/ --fix

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info xray_pilot.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

# Build package for release
build: clean
	python -m build

# === Isolated Dev Proxy (ports 2080/2087, no system proxy) ===

dev-proxy:
	bash dev/dev-proxy.sh start

dev-proxy-node:
	bash dev/dev-proxy.sh start $(NODE)

dev-proxy-stop:
	bash dev/dev-proxy.sh stop

dev-proxy-restart:
	bash dev/dev-proxy.sh restart

dev-proxy-restart-node:
	bash dev/dev-proxy.sh restart $(NODE)

dev-proxy-status:
	bash dev/dev-proxy.sh status

dev-proxy-nodes:
	bash dev/dev-proxy.sh nodes

dev-proxy-test:
	bash dev/dev-proxy.sh test

# === Docker (if available) ===

# Build Docker image
docker-build:
	docker build -t xray-pilot-dev .

# Run in Docker with network isolation
docker-run:
	docker run --rm -it \
		--network bridge \
		-p 1080:1080 \
		-p 1087:1087 \
		-v $(PWD):/app \
		xray-pilot-dev

# Enter Docker shell for development
docker-shell:
	docker run --rm -it \
		--network bridge \
		-v $(PWD):/app \
		xray-pilot-dev /bin/bash
