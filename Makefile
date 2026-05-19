.PHONY: help dev-build dev-shell terraform-init terraform-plan terraform-apply terraform-destroy \
        ansible-check ansible-deploy docs venv \
        test test-cov test-report test-integration test-clean \
        terraform-fmt-check terraform-validate-all lint-terraform \
        ansible-syntax-check lint-ansible \
        lint clean

# Use venv Python when available, otherwise fall back to system python3
PYTHON := $(shell [ -f venv/bin/python3 ] && echo venv/bin/python3 || echo python3)

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

# Testing
venv: ## Create virtualenv and install all dependencies
	python3 -m venv venv
	venv/bin/pip install --quiet --upgrade pip
	venv/bin/pip install --quiet -r requirements.txt
	@echo "Virtualenv ready. Re-run make commands to use it."

test: ## Run unit tests — no real services needed (creates venv if missing)
	@[ -f venv/bin/python3 ] || $(MAKE) venv
	$(PYTHON) -m pytest tests/ -v -m "not integration"

test-cov: ## Run unit tests with coverage report (fails below 80%)
	@[ -f venv/bin/python3 ] || $(MAKE) venv
	$(PYTHON) -m pytest tests/ --cov --cov-report=term-missing -m "not integration"

test-report: ## Generate HTML coverage report (unit tests only)
	@[ -f venv/bin/python3 ] || $(MAKE) venv
	$(PYTHON) -m pytest tests/ --cov --cov-report=html -m "not integration"
	@echo "Coverage report available at htmlcov/index.html"

test-integration: ## Run integration tests (requires env vars — see docs/TESTING.md)
	@[ -f venv/bin/python3 ] || $(MAKE) venv
	$(PYTHON) -m pytest tests/integration/ -v -m integration

test-clean: ## Remove test artifacts (.coverage, htmlcov/, .pytest_cache/)
	find . -name ".coverage" -delete
	find . -name "htmlcov" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Full Deployment
deploy: ## Full deployment (terraform + ansible)
	chmod +x scripts/deploy.sh
	./scripts/deploy.sh apply

destroy: ## Destroy everything
	chmod +x scripts/deploy.sh
	./scripts/deploy.sh destroy

# Terraform static analysis
terraform-fmt-check: ## Check Terraform formatting (no changes applied)
	@for dir in terraform/example terraform/PVE-HOME/pve-home-clab01 terraform/PVE-HOME/pve-home-n8n01 \
	            terraform/PVE-HOME/pve-home-nbox01 terraform/PVE-HOME/pve-home-netobs01 \
	            terraform/PVE-HOME/pve-home-zt-netops01; do \
	    [ -d "$$dir" ] && echo "fmt-check: $$dir" && terraform fmt -check "$$dir" || true; \
	done

terraform-validate-all: ## Validate all Terraform modules (no backend, no real credentials)
	@for dir in terraform/example terraform/PVE-HOME/pve-home-clab01 terraform/PVE-HOME/pve-home-n8n01 \
	            terraform/PVE-HOME/pve-home-nbox01 terraform/PVE-HOME/pve-home-netobs01 \
	            terraform/PVE-HOME/pve-home-zt-netops01; do \
	    if [ -d "$$dir" ]; then \
	        echo "validate: $$dir"; \
	        terraform -chdir="$$dir" init -backend=false -input=false -no-color > /dev/null 2>&1 && \
	        terraform -chdir="$$dir" validate -no-color || true; \
	    fi; \
	done

lint-terraform: ## Run all Terraform static analysis (fmt + validate + checkov)
	@[ -f venv/bin/python3 ] || $(MAKE) venv
	@[ -f venv/bin/checkov ] || venv/bin/pip install --quiet checkov
	$(MAKE) terraform-fmt-check
	$(MAKE) terraform-validate-all
	@echo "Running checkov on terraform/..."
	$(PYTHON) -m checkov -d terraform --soft-fail --quiet
	@if command -v tflint >/dev/null 2>&1; then \
	    echo "Running tflint..."; \
	    for dir in terraform/example terraform/PVE-HOME/pve-home-clab01 terraform/PVE-HOME/pve-home-n8n01 \
	               terraform/PVE-HOME/pve-home-nbox01 terraform/PVE-HOME/pve-home-netobs01 \
	               terraform/PVE-HOME/pve-home-zt-netops01; do \
	        [ -d "$$dir" ] && tflint --chdir="$$dir" || true; \
	    done; \
	else \
	    echo "tflint not installed — skipping (see docs/TESTING.md for install instructions)"; \
	fi

# Ansible static analysis
ansible-syntax-check: ## Syntax-check every deploy.yml playbook (no inventory needed)
	@for playbook in ansible/*/deploy.yml ansible/*/deploy_server.yml; do \
	    [ -f "$$playbook" ] && echo "syntax-check: $$playbook" && \
	    ansible-playbook --syntax-check "$$playbook" 2>&1 | grep -v '^$' || true; \
	done

lint-ansible: ## Run ansible-lint and yamllint across ansible/
	@[ -f venv/bin/python3 ] || $(MAKE) venv
	@[ -f venv/bin/ansible-lint ] || venv/bin/pip install --quiet ansible-lint yamllint
	@echo "Running ansible-lint..."
	venv/bin/ansible-lint ansible/
	@echo "Running yamllint..."
	venv/bin/yamllint -c .yamllint.yml ansible/ || [ $$? -eq 1 ]

# Umbrella lint target
lint: ## Run all static analysis (terraform + ansible)
	$(MAKE) lint-terraform
	$(MAKE) lint-ansible

# Cleanup
clean: ## Clean temporary files (includes test artifacts)
	find . -name "*.tfstate*" -type f -delete
	find . -name "*.retry" -type f -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name ".coverage" -delete
	find . -name "htmlcov" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true

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
