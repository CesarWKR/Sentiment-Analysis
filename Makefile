# Variables
DOCKER_USER ?= $(shell echo $$DOCKER_USERNAME)
DOCKER_PASS ?= $(shell echo $$DOCKER_PASSWORD)
VERSION = latest
SLIM_TAG = slim-$(VERSION)
COMPOSE_FILE = docker-compose.yml
ENV_FILE = .env

REQUIRED_TOOLS = docker docker-compose docker-slim

# Services with their own builds
SERVICES = pipeline inference_api
# Images
IMAGE_pipeline = sentiment_pipeline
IMAGE_inference_api = sentiment_inference_api

# Slim ONLY inference
SLIM_SERVICES = inference_api


#VERSION = latest

check-tools:
	@for tool in $(REQUIRED_TOOLS); do \
		command -v $$tool >/dev/null 2>&1 || { echo "❌ $$tool is not installed."; exit 1; }; \
	done
	@echo "✅ All required tools are installed."


# Validate
ifndef DOCKER_USER
$(error ❌ DOCKER_USER is undefined. Please set it as an environment variable or in the Makefile)
endif
ifndef DOCKER_PASS
$(error ❌ DOCKER_PASS is undefined. Please set it as an environment variable or in the Makefile)
endif


# Docker login
login:
	@echo "🔑 Logging into DockerHub as $(DOCKER_USER)..."
	@echo "$(DOCKER_PASS)" | docker login -u "$(DOCKER_USER)" --password-stdin
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
	@for service in $(SLIM_SERVICES); do \
		image=$$(eval echo \$$(IMAGE_$$service)); \
		if docker image inspect $$image:$(VERSION) >/dev/null 2>&1; then \
			echo "⚡ Running docker-slim for: $$image:$(VERSION)"; \
			docker-slim slim build \
				--http-probe=false \
				--exec-file=false \
				--tag $$image:$(SLIM_TAG) \
				$$image:$(VERSION); \
		else \
			echo "❌ Local image $$image:$(VERSION) not found. Skipping."; \
		fi \
	done


# Clean up docker-slim temporary files
slim-clean:
	@rm -rf slim.report.json slim.debug* slim.output.json || true

# Tag slim images for DockerHub
tag:
	@for service in $(SLIM_SERVICES); do \
		image=$$(eval echo \$$(IMAGE_$$service)); \
		echo "🏷️ Tagging $$image:$(SLIM_TAG)"; \
		docker tag $$image:$(SLIM_TAG) $(DOCKER_USER)/$$image:$(SLIM_TAG); \
	done

# Push slim images to DockerHub
push:
	@for service in $(SLIM_SERVICES); do \
		image=$$(eval echo \$$(IMAGE_$$service)); \
		echo "🚀 Pushing $$image to DockerHub"; \
		docker push $(DOCKER_USER)/$$image:$(SLIM_TAG); \
	done

# Complete workflow: Build + Slim + Tag + Push
publish: check-tools build slim tag push
	@echo "✅ Publishing: version $(SLIM_TAG)"


# Check images
images:
	@docker images | grep -E "$(VERSION)|$(SLIM_TAG)" || true

# Clean up all services
clean:
	@for service in $(SERVICES); do \
		echo "🧼 Deleting images for $$service..."; \
		docker rmi $$service:$(VERSION) || true; \
		docker rmi $$service:$(SLIM_TAG) || true; \
		docker rmi $(DOCKER_USER)/$$service:$(SLIM_TAG) || true; \
	done