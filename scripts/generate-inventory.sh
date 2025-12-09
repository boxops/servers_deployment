#!/bin/bash
# 
# Ansible Inventory Generator
# 
# Simple wrapper script to generate Ansible inventory from Terraform deployments
# 

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🔍 Generating Ansible inventory from Terraform deployments..."

# Run the inventory generation
cd "$PROJECT_DIR"
python3 ansible_new/scripts/generate_inventory_from_tf.py "$@"

echo ""
echo "📋 Inventory generated successfully!"
echo "   File: ansible_new/inventories/production/hosts.yml"
echo ""
echo "💡 Usage examples:"
echo "   ansible-inventory -i ansible_new/inventories/production/hosts.yml --list"
echo "   ansible all -i ansible_new/inventories/production/hosts.yml --list-hosts"
echo "   ansible bind9_servers -i ansible_new/inventories/production/hosts.yml -m ping"