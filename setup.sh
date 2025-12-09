#!/bin/bash

# Infrastructure Deployment Setup Script
# This script initializes the project and sets up the development environment

set -e

PROJECT_ROOT=$(pwd)
echo "=== Infrastructure Deployment Setup ==="
echo "Project root: $PROJECT_ROOT"

# Make scripts executable
echo "Making scripts executable..."
chmod +x scripts/*.sh scripts/*.py

# Create terraform.tfvars from example if it doesn't exist
if [ ! -f "terraform/terraform.tfvars" ]; then
    echo "Creating terraform.tfvars from example..."
    cp terraform/terraform.tfvars.example terraform/terraform.tfvars
    echo "✓ Created terraform/terraform.tfvars"
    echo "  Please edit this file with your Proxmox configuration"
else
    echo "✓ terraform.tfvars already exists"
fi

# Create SSH key directory structure
if [ ! -d "$HOME/.ssh" ]; then
    echo "Creating SSH directory..."
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    echo "✓ Created ~/.ssh directory"
    echo "  Please add your SSH keys to ~/.ssh/"
else
    echo "✓ SSH directory exists"
fi

# Check if running in WSL and provide specific instructions
if grep -qi microsoft /proc/version 2>/dev/null; then
    echo ""
    echo "=== WSL Environment Detected ==="
    echo "For Windows users, you can either:"
    echo "1. Use the Dev Container in VS Code (recommended)"
    echo "2. Use Docker Compose: docker-compose run --rm infrastructure-dev"
    echo "3. Install dependencies in WSL directly"
fi

echo ""
echo "=== Next Steps ==="
echo "1. Edit terraform/terraform.tfvars with your Proxmox configuration"
echo "2. Ensure your SSH keys are in ~/.ssh/"
echo "3. Choose your development environment:"
echo "   - Dev Container: Open in VS Code with Dev Container extension"
echo "   - Docker: Run 'make dev-build && make dev-shell'"
echo "   - Local: Install Terraform and Ansible locally"
echo "4. Deploy: Run 'make deploy' when ready"
echo ""
echo "For help: make help"
echo "Setup complete! 🚀"
