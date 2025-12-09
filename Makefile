.PHONY: help dev-build dev-shell terraform-init terraform-plan terraform-apply terraform-destroy ansible-check ansible-deploy docs clean

# Default target
help: ## Show this help message
	@echo "Infrastructure Deployment Makefile"
	@echo "===================================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Development Environment
dev-build: ## Build the development Docker container
	docker compose build

dev-shell: ## Start a shell in the development container
	docker compose run --rm infrastructure-dev

dev-clean: ## Remove development containers and images
	docker compose down --rmi all --volumes

# Terraform Commands
terraform-init: ## Initialize Terraform
	cd terraform && terraform init

terraform-plan: ## Plan Terraform deployment
	cd terraform && terraform plan

terraform-apply: ## Apply Terraform deployment
	cd terraform && terraform apply

terraform-destroy: ## Destroy Terraform infrastructure
	cd terraform && terraform destroy

# Ansible Commands
ansible-check: ## Check Ansible syntax and connectivity
	cd ansible && ansible-playbook -i inventories/hosts.yml site.yml --check --diff

ansible-deploy: ## Deploy with Ansible
	cd ansible && ansible-playbook -i inventories/hosts.yml site.yml

# Documentation
docs: ## Generate architecture documentation from current deployment
	python3 scripts/generate-docs.py

# Full Deployment
deploy: ## Full deployment (terraform + ansible)
	chmod +x scripts/deploy.sh
	./scripts/deploy.sh apply

destroy: ## Destroy everything
	chmod +x scripts/deploy.sh
	./scripts/deploy.sh destroy

# Cleanup
clean: ## Clean temporary files
	find . -name "*.tfstate*" -type f -delete
	find . -name "*.retry" -type f -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Setup
setup: ## Initial project setup
	@echo "Setting up infrastructure deployment project..."
	@if [ ! -f terraform/terraform.tfvars ]; then \
		cp terraform/terraform.tfvars.example terraform/terraform.tfvars; \
		echo "Created terraform/terraform.tfvars from example. Please edit it with your values."; \
	fi
	@chmod +x scripts/*.sh scripts/*.py
	@mkdir -p docs
	@echo "Setup complete! Edit terraform/terraform.tfvars and run 'make deploy'"
	@echo "After deployment, run 'make docs' to generate architecture documentation"
