#!/bin/bash

# Install Ansible
sudo apt-get update
sudo apt-get install -y software-properties-common
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt-get install -y ansible

# Install additional Python packages for Ansible MySQL modules
sudo apt-get install -y python3-pip
pip3 install pymysql

# Install Terraform (specific version as required)
wget -O /tmp/terraform.zip https://releases.hashicorp.com/terraform/1.5.0/terraform_1.5.0_linux_amd64.zip
sudo unzip /tmp/terraform.zip -d /usr/local/bin/
sudo chmod +x /usr/local/bin/terraform

# Install SSH client
sudo apt-get install -y openssh-client

# Create necessary directories
mkdir -p /home/vscode/.ssh
chmod 700 /home/vscode/.ssh

echo "Development environment setup complete!"
echo "Terraform version: $(terraform --version)"
echo "Ansible version: $(ansible --version)"
