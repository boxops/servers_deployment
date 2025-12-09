# VM Deployment Guide

**A step-by-step guide for deploying virtual machines using Terraform**

## Table of Contents

- [🎯 Prerequisites](#prerequisites)
- [🚀 Quick Start](#quick-start)
- [📋 Step-by-Step Deployment](#step-by-step-deployment)
- [🔧 Configuration Examples](#configuration-examples)
- [🎛️ Advanced Configurations](#advanced-configurations)
- [❓ Troubleshooting](#troubleshooting)

---

## Prerequisites

Before deploying VMs, ensure you have:

### ✅ Proxmox Environment
- [ ] Proxmox VE 7.0+ with administrative access
- [ ] API token created (Datacenter → Permissions → API Tokens)
- [ ] Ubuntu 22.04 LTS template available (see [Template Creation Guide](../README.md#vm-template-creation-guide))
- [ ] Available IP addresses in your network

### ✅ Development Environment
- [ ] Terraform v1.5.0+ installed
- [ ] SSH key pair generated (`ssh-keygen -t rsa -b 4096`)
- [ ] Git repository cloned and accessible
- [ ] Network connectivity to Proxmox host

### ✅ Network Planning
- [ ] IP address range documented
- [ ] Gateway and DNS servers identified
- [ ] VLAN configurations (if applicable)
- [ ] Firewall rules planned

---

## Quick Start

### 1. Choose Your Deployment

**For beginners**: Start with the example template
```bash
cd terraform/example
```

**For specific services**: Use pre-configured VMs
```bash
cd terraform/PROXMOX-NODE-01/node01-grafana  # Grafana server example
```

### 2. Configure and Deploy

```bash
# Copy and edit configuration
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars

# Deploy
terraform init
terraform apply
```

### 3. Verify Deployment

```bash
# Check outputs
terraform output

# Test SSH connectivity
ssh ubuntu@$(terraform output -raw vm_ip_address)
```

---

## Step-by-Step Deployment

### Step 1: Understand the Terraform Structure

Each VM deployment consists of:

```
vm-deployment/
├── main.tf               # VM resource definition
├── variables.tf          # Input variable definitions  
├── outputs.tf            # Output values after deployment
├── terraform.tfvars      # Your specific configuration
└── terraform.tfvars.example  # Example configuration
```

### Step 2: Configure Your Deployment

Create your `terraform.tfvars` file:

```hcl
# Proxmox API Configuration
proxmox_api_url          = "https://your-proxmox-host:8006/api2/json"
proxmox_api_token_id     = "terraform@pve!mytoken"
proxmox_api_token_secret = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
proxmox_node             = "proxmox-node-01"

# VM Configuration
vm_name        = "my-service-vm"
vm_id          = 150                    # Must be unique across Proxmox
vm_template    = "ubuntu-cloud"         # Must exist in Proxmox
vm_memory      = 4096                   # Memory in MB
vm_cores       = 2                      # CPU cores
vm_disk_size   = "32G"                  # Primary disk size

# Network Configuration
vm_ip_address  = "10.0.1.X/24"     # IP with CIDR notation
vm_gateway     = "10.0.1.1"          # Network gateway
vm_nameserver  = "8.8.8.8"             # DNS server
vm_bridge      = "vmbr0"               # Proxmox network bridge

# SSH Configuration
ssh_public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... your-public-key"
```

### Step 3: Validate Configuration

```bash
# Initialize Terraform (downloads providers)
terraform init

# Validate syntax
terraform validate

# Preview changes
terraform plan
```

### Step 4: Deploy the VM

```bash
# Apply configuration
terraform apply

# Type 'yes' when prompted, or use auto-approve
terraform apply -auto-approve
```

### Step 5: Verify Deployment

```bash
# Check Terraform outputs
terraform output

# Test VM connectivity
ping $(terraform output -raw vm_ip_address)

# SSH to the VM
ssh ubuntu@$(terraform output -raw vm_ip_address)
```

---

## Configuration Examples

### Basic Web Server

```hcl
# terraform.tfvars
vm_name       = "web-server-01"
vm_id         = 201
vm_memory     = 2048
vm_cores      = 2
vm_ip_address = "10.0.1.201/24"
```

### Database Server

```hcl
# terraform.tfvars  
vm_name       = "db-server-01"
vm_id         = 301
vm_memory     = 8192
vm_cores      = 4
vm_disk_size  = "64G"
vm_ip_address = "10.0.1.301/24"

# Additional data disk
vm_additional_disks = [
  {
    storage = "local-lvm"
    size    = "100G"
    format  = "raw"
  }
]
```

### High-Performance Service

```hcl
# terraform.tfvars
vm_name       = "app-server-01" 
vm_id         = 401
vm_memory     = 16384
vm_cores      = 8
vm_sockets    = 2
vm_numa       = true
vm_cpu_type   = "host"
vm_ip_address = "10.0.1.401/24"
```

### Multi-Network VM

```hcl
# main.tf modification for multiple network interfaces
network {
  model  = "virtio"
  bridge = "vmbr0"
  tag    = 100  # VLAN tag
}

network {
  model  = "virtio" 
  bridge = "vmbr1"
  tag    = 200  # Different VLAN
}

# terraform.tfvars
vm_ip_address = "10.0.100.150/24"  # First interface
# Second interface configured via cloud-init user-data
```

---

## Advanced Configurations

### Custom Cloud-Init Configuration

Create advanced VM customizations:

```hcl
# In main.tf, add custom cloud-init
ciuser = "admin"
cipassword = "secure-password"
cicustom = "user=local:snippets/user-data-cloud-config.yml"
searchdomain = "example.com"
nameserver = "10.0.1.1 8.8.8.8"
```

### VM Templates with Specific Configurations

```hcl
# Use specialized templates
vm_template = "ubuntu-cloud-docker"    # Pre-installed Docker
vm_template = "ubuntu-cloud-k8s"       # Kubernetes-ready
vm_template = "ubuntu-cloud-minimal"   # Minimal installation
```

### Resource Constraints and Limits

```hcl
# CPU limits
cpu {
  cores   = 4
  sockets = 1
  numa    = true
  limit   = 2000  # CPU limit (MHz)
  units   = 1000  # CPU weight
}

# Memory settings
memory = 8192
balloon = 4096  # Balloon minimum memory
```

### High Availability Configuration

```hcl
# HA settings
onboot = true
protection = true
startup = "order=1,up=30"  # Boot order and delay
```

---

## Multiple VM Deployment

### Deploy VM Fleet

Create multiple VMs with consistent configuration:

```hcl
# variables.tf
variable "vm_instances" {
  type = map(object({
    vm_id         = number
    memory        = number
    cores         = number
    ip_address    = string
  }))
}

# terraform.tfvars
vm_instances = {
  "web-01" = {
    vm_id      = 201
    memory     = 2048
    cores      = 2
    ip_address = "10.0.1.201/24"
  },
  "web-02" = {
    vm_id      = 202
    memory     = 2048
    cores      = 2
    ip_address = "10.0.1.202/24"
  }
}

# main.tf
resource "proxmox_vm_qemu" "vm_fleet" {
  for_each = var.vm_instances
  
  name        = each.key
  vmid        = each.value.vm_id
  memory      = each.value.memory
  cores       = each.value.cores
  
  # Network configuration
  ipconfig0 = "ip=${each.value.ip_address},gw=${var.vm_gateway}"
  
  # ... other configuration
}
```

---

## Troubleshooting

### Common Deployment Issues

#### VM ID Already Exists
```
Error: VM with ID XXX already exists
```
**Solution**: Choose a unique VM ID or destroy existing VM:
```bash
# Check existing VMs
qm list
# Use different vm_id in terraform.tfvars
```

#### Template Not Found
```
Error: template 'ubuntu-cloud' not found
```
**Solution**: Verify template exists:
```bash
# List templates on Proxmox
qm list | grep template
# Update vm_template in terraform.tfvars
```

#### Network Configuration Issues
```
Error: VM deployed but not reachable
```
**Solution**: Check network settings:
```bash
# Verify network configuration
ssh -o ConnectTimeout=5 ubuntu@vm_ip_address
# Check via Proxmox console if SSH fails
```

#### Authentication Issues  
```
Error: authentication failed
```
**Solution**: Verify API credentials:
```bash
# Test API connectivity
curl -k -d "username=terraform@pve&password=api_secret" \
  https://proxmox-host:8006/api2/json/access/ticket
```

### Deployment Validation

#### Pre-Deployment Checks

```bash
# Validate Terraform configuration
terraform validate

# Check resource availability
terraform plan -out=plan.tfplan

# Verify template exists
# (Run on Proxmox host)
qm config template_id
```

#### Post-Deployment Verification

```bash
# Verify VM is running
terraform output
qm status $(terraform output -raw vm_id)

# Test network connectivity
ping $(terraform output -raw vm_ip_address)

# Verify SSH access
ssh -o ConnectTimeout=10 ubuntu@$(terraform output -raw vm_ip_address) 'uname -a'
```

### Recovery Procedures

#### VM Deployment Failed
```bash
# Clean up failed deployment
terraform destroy

# Fix configuration issues
nano terraform.tfvars

# Retry deployment
terraform apply
```

#### VM Partially Configured
```bash
# Force recreation
terraform taint proxmox_vm_qemu.vm_name
terraform apply
```

#### State Inconsistency
```bash
# Refresh state to match reality
terraform refresh

# Import existing VM if needed
terraform import proxmox_vm_qemu.vm_name node/qemu/VMID
```

---

## Next Steps

After successful VM deployment:

1. **Service Installation**: Use Ansible playbooks to configure services
2. **Monitoring Setup**: Add VM to monitoring systems
3. **Backup Configuration**: Set up automated backups
4. **Documentation**: Update infrastructure documentation

For service configuration, see the [Service Management Guide](SERVICE_MANAGEMENT_GUIDE.md).