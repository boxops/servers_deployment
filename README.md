# Infrastructure Deployment & Management Platform

Enterprise-grade infrastructure deployment and service management platform using Terraform and Ansible on Proxmox VE.

## Overview

This project provides a comprehensive Infrastructure as Code (IaC) solution for deploying and managing enterprise network services on Proxmox VE. The platform automates VM provisioning, service configuration, and ongoing management through declarative configuration.

### Supported Services

- **🌐 DNS**: BIND9 authoritative and recursive DNS servers
- **📊 Monitoring**: Full monitoring infrastructure with MySQL backend
- **📈 Visualization**: Grafana dashboards and analytics
- **🏠 IPAM/DCIM**: NetBox for IP and datacenter management
- **🔧 Config Management**: Oxidized for network device backup
- **📡 Wireless**: UniFi and UISP controllers
- **🔄 DHCP**: Kea DHCP with PostgreSQL backend and HA
- **🔐 Authentication**: FreeRADIUS and OpenLDAP
- **📁 Services**: FTP servers, device management
- **🖥️ Server Management**: Linux server lifecycle and monitoring

## Architecture

The platform uses a layered architecture:

- **Infrastructure Layer**: Proxmox VE with Terraform-managed VM lifecycle
- **Configuration Layer**: Ansible-based deployment and configuration
- **Service Layer**: Containerized and native services with health monitoring
- **Management Layer**: Centralized logging, monitoring, and orchestration

📋 **Detailed Documentation**: See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for complete architecture

## Quick Start

### Prerequisites

- **Proxmox VE** 7.0+ with API access
- **Ubuntu 22.04 LTS** VM template with cloud-init support
- **Terraform** v1.5.0+ and **Ansible** v2.9+
- **Python** 3.8+ with `pymysql`, `psycopg2`, `requests`, `netaddr`
- **SSH Key Pair** for VM access

### Setup

```bash
# Clone repository
git clone <repository-url>
cd servers_deployment

# Run setup script
./setup.sh

# Configure Terraform variables
cp terraform/example/terraform.tfvars.example terraform/example/terraform.tfvars
nano terraform/example/terraform.tfvars
```

### Create VM Template

```bash
# SSH to Proxmox host
ssh root@proxmox-host

# Download Ubuntu cloud image
cd /var/lib/vz/template/iso/
wget https://cloud-images.ubuntu.com/jammy/current/jammy-server-cloudimg-amd64.img

# Create VM from cloud image
qm create 9000 --name ubuntu-cloud-22.04 --memory 2048 --cores 2 --net0 virtio,bridge=vmbr0
qm importdisk 9000 jammy-server-cloudimg-amd64.img local-lvm
qm set 9000 --scsihw virtio-scsi-pci --scsi0 local-lvm:vm-9000-disk-0
qm set 9000 --ide2 local-lvm:cloudinit
qm set 9000 --boot c --bootdisk scsi0
qm set 9000 --serial0 socket --vga serial0
qm set 9000 --agent enabled=1
qm template 9000
```

### Deploy Infrastructure

```bash
# Using Terraform
cd terraform/example
terraform init
terraform plan
terraform apply

# Using Ansible for service configuration
cd ansible/<service-name>
ansible-playbook -i inventories/production/hosts.yml deploy.yml
```

### Using Development Container

```bash
# With Docker Compose
make dev-build
make dev-shell

# Or open in VS Code Dev Container
# VS Code will detect .devcontainer/devcontainer.json automatically
```

## Project Structure

```
servers_deployment/
├── ansible/              # Service-specific Ansible playbooks and roles
│   ├── bind9/           # DNS services
│   ├── kea_dhcp/        # DHCP services
│   ├── netbox/          # IPAM/DCIM
│   ├── grafana/         # Visualization
│   └── ...              # Other services
├── terraform/           # Infrastructure as Code
│   ├── PVE-HOME/        # Lab environment
│   └── example/         # Example templates
├── docs/                # Documentation
├── scripts/             # Automation scripts
└── Makefile            # Common automation tasks
```

## Common Tasks

### Deploy a Service

```bash
# Navigate to service directory
cd ansible/kea_dhcp

# Deploy to production
ansible-playbook -i inventories/production/hosts.yml deploy_server.yml

# Run health check
ansible-playbook -i inventories/production/hosts.yml health_check.yml
```

### Update Service Configuration

```bash
cd ansible/<service-name>

# Update configuration files in intended_configs/
# Then deploy changes
ansible-playbook -i inventories/production/hosts.yml update_config.yml
```

### Generate Documentation

```bash
# Auto-generate architecture documentation from current deployment
make docs
```

## Service Management

Each service follows a standardized structure:

- `deploy.yml` - Initial service deployment
- `update_config.yml` - Configuration updates
- `health_check.yml` - Service health validation
- `inventories/` - Environment-specific hosts
- `roles/` - Reusable automation components
- `intended_configs/` - Desired configuration files

See [docs/SERVICE_MANAGEMENT_GUIDE.md](docs/SERVICE_MANAGEMENT_GUIDE.md) for detailed patterns.

## Development

### Using Makefile

```bash
make help              # Show all available commands
make dev-build         # Build dev container
make dev-shell         # Start dev shell
make terraform-init    # Initialize Terraform
make terraform-plan    # Plan infrastructure changes
make ansible-check     # Check Ansible syntax
make docs              # Generate documentation
```

### Multi-Environment Support

The platform supports multiple environments:

- `production/` - Production infrastructure
- `lab/` - Testing and development
- `staging/` - Pre-production validation

Configure environment-specific variables in respective `inventories/` directories.

## Best Practices

1. **Version Control**: Always commit configuration changes before applying
2. **Idempotent Operations**: All playbooks are safe to run multiple times
3. **Health Checks**: Run health checks after deployments
4. **Backups**: Use `copy_actual_to_intended.yml` to backup current configs
5. **Testing**: Test changes in lab environment first

## Contributing

1. Create feature branch from `main`
2. Make changes following project conventions
3. Test in lab environment
4. Submit pull request with clear description

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md) - Complete architecture overview
- [Service Management Guide](docs/SERVICE_MANAGEMENT_GUIDE.md) - Service lifecycle patterns
- [VM Deployment Guide](docs/VM_DEPLOYMENT_GUIDE.md) - Terraform deployment guide

## License

See [LICENSE](LICENSE) file for details.

---

**Questions or Issues?** Please open an issue in the repository.
