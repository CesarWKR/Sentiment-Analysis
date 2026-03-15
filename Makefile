# leer .env si existe; las asignaciones pasan a variables de make
-include .env

# asegurar que las variables se exportan al entorno de los comandos
export DOCKER_USERNAME DOCKER_PASSWORD

# Variables
DOCKER_USERNAME ?= $(shell echo $$DOCKER_USERNAME)
DOCKER_PASSWORD ?= $(shell echo $$DOCKER_PASSWORD)
VERSION = latest
# SLIM_TAG = slim-$(VERSION)
COMPOSE_FILE = docker-compose.yml
ENV_FILE = .env

REQUIRED_TOOLS = docker docker-compose docker-slim

# Services with their own builds
SERVICES = pipeline inference_api
# Images
IMAGE_pipeline = sentiment_pipeline
IMAGE_inference_api = sentiment_inference_api

# Slim ONLY inference
# SLIM_SERVICES = inference_api


#VERSION = latest

check-tools:
	@for tool in $(REQUIRED_TOOLS); do \
		command -v $$tool >/dev/null 2>&1 || { echo "❌ $$tool is not installed."; exit 1; }; \
	done
	@echo "✅ All required tools are installed."


# Validate
ifndef DOCKER_USERNAME
$(error ❌ DOCKER_USERNAME is undefined. Please set it as an environment variable or in the Makefile)
endif
ifndef DOCKER_PASSWORD
$(error ❌ DOCKER_PASSWORD is undefined. Please set it as an environment variable or in the Makefile)
endif


# Docker login
login:
	@echo "🔑 Logging into DockerHub as $(DOCKER_USERNAME)..."
	@echo "$(DOCKER_PASSWORD)" | docker login -u "$(DOCKER_USERNAME)" --password-stdin
	@echo "✅ Docker login successful."


# Build individual service images
build-%:
	@echo "🔨 Building image for $*"
	@docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) build $*


# Build all services
build:
	@for service in $(SERVICES); do \
		$(MAKE) build-$$service; \
	done


# Start all services in detached mode
up:
	@docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) up -d

# Stop all services 
down:
	@docker compose -f $(COMPOSE_FILE) --env-file $(ENV_FILE) down


# Optimize images with docker-slim
slim:
	@image=$(IMAGE_inference_api); \
	echo "⚡ Running docker-slim for: $$image:$(VERSION)"; \
	docker-slim build \
		--http-probe=false \
		--tag $$image:$(SLIM_TAG) \
		$$image:$(VERSION);


# Clean up docker-slim temporary files
slim-clean:
	@rm -rf slim.report.json slim.debug* slim.output.json || true

# Tag slim images for DockerHub
tag:
	@image=$(IMAGE_inference_api); \
	echo "🏷️ Tagging $$image:$(VERSION) as $(DOCKER_USERNAME)/$$image:$(VERSION)"; \
	docker tag $$image:$(VERSION) $(DOCKER_USERNAME)/$$image:$(VERSION);

# Push images to DockerHub
push:
	@image=$(IMAGE_inference_api); \
	echo "🚀 Pushing $$image:$(VERSION) to DockerHub"; \
	docker push $(DOCKER_USERNAME)/$$image:$(VERSION);

# Complete workflow: Build + Tag + Push
publish: check-tools build tag push
	@echo "✅ Publishing: version $(VERSION)"


# Check images
images:
	@docker images | grep -E "$(VERSION)|$(SLIM_TAG)" || true

# Clean up all services
clean:
	@for service in $(SERVICES); do \
		echo "🧼 Deleting images for $$service..."; \
		docker rmi $$service:$(VERSION) || true; \
		docker rmi $$service:$(SLIM_TAG) || true; \
		docker rmi $(DOCKER_USERNAME)/$$service:$(VERSION) || true; \
	done