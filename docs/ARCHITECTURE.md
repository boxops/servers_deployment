# Enterprise Infrastructure Architecture

*Generated on 2025-10-30 - Comprehensive Service Platform*

## 🏗️ Platform Overview

This document describes the enterprise infrastructure deployment platform that provides comprehensive service management using Infrastructure as Code (IaC) principles with Terraform and Ansible on Proxmox VE.

### Platform Summary
- **Infrastructure Provider**: Proxmox VE 7.0+ cluster  
- **Deployment Method**: Terraform + Ansible automation
- **Service Coverage**: 15+ enterprise services
- **Multi-Environment**: Production, Lab, and Staging support
- **High Availability**: Cross-node deployment with failover capabilities

## 🌐 Network Architecture

### Multi-Node Proxmox Infrastructure

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      Enterprise Service Platform                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌─────────── PROXMOX-NODE-01 ─────────────┐   ┌────── PROXMOX-NODE-02 ──────────┐  │
│  │                                       │   │                               │  │
│  │  🌐 BIND DNS (Primary)               │   │  🌐 BIND DNS (Secondary)      │  │
│  │  ├── Authoritative DNS                │   │  ├── Authoritative DNS        │  │
│  │  └── Zone Management                  │   │  └── HA Failover              │  │
│  │                                       │   │                               │  │
│  │  📊 Grafana Visualization             │   │  🏠 NetBox IPAM              │  │
│  │  ├── Dashboards & Analytics           │   │  ├── IP Management            │  │
│  │  └── Multi-source Data                │   │  └── DCIM Platform            │  │
│  │                                       │   │                               │  │
│  │  🔧 Network Management                │   │  🔧 Oxidized Config Backup   │  │
│  │  ├── UISP Platform                    │   │  ├── Device Configuration     │  │
│  │  └── ISP Operations                   │   │  └── Version Control          │  │
│  │                                       │   │                               │  │
│  │  🏠 NetBox IPAM (Backup)              │   │  🖥️  Jump Host                │  │
│  │  └── Secondary IPAM                   │   │  ├── Secure Access Point      │  │
│  └───────────────────────────────────────┘   │  └── Administrative Tasks     │  │
│                                              │  ⚡ Firmware Management       │  │
│                                              │  ├── Centralized Updates      │  │ 
│                                              │  └── Version Tracking         │  │
│                                              └───────────────────────────────┘  │
│                                                                                 │
│  ┌─────────────────── Service Distribution ──────────────────────────────────┐  │
│  │                                                                           │  │
│  │  🔄 DHCP Services (Distributed)    🔐 Authentication Services            │  │
│  │  ├── Kea DHCP Primary             ├── FreeRADIUS                          │  │
│  │  ├── Kea DHCP Secondary           └── OpenLDAP Directory                  │  │
│  │  └── PostgreSQL Backend                                                   │  │
│  │                                   📁 File Services                        │  │
│  │  🔧 Device Management            ├── FTP Servers                          │  │
│  │  ├── Generic Device Automation   └── File Storage                         │  │
│  │  └── Tachyon Integration                                                  │  │
│  └───────────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## 🏢 Service Portfolio

### Core Network Services

#### 🌐 DNS Infrastructure (BIND9)
- **Primary DNS**: PROXMOX-NODE-01 (Authoritative zones, recursive queries)
- **Secondary DNS**: PROXMOX-NODE-02 (HA failover, zone transfers) 
- **Features**: Dynamic zone updates, DNSSEC, query analytics
- **Management**: Automated zone deployment from NetBox integration

#### 🔄 DHCP Services (Kea DHCP)
- **Primary DHCP**: dhcp-primary (10.0.1.91)
- **Secondary DHCP**: dhcp-secondary (10.0.2.91)
- **Backend**: PostgreSQL with lease tracking and statistics
- **Features**: High availability, RESTful API, subnet automation
- **Integration**: NetBox IPAM synchronization

### 📊 Monitoring & Visualization

#### 📊 Grafana Visualization
- **Grafana Server**: PROXMOX-NODE-01 (Dashboard platform)
- **Features**: Multi-source dashboards, alerting, user management
- **Integration**: NetBox and custom data sources

### 🏠 Infrastructure Management

#### 🏠 NetBox IPAM/DCIM
- **Primary NetBox**: PROXMOX-NODE-02 (IPAM and DCIM management)
- **Backup NetBox**: PROXMOX-NODE-01 (Redundancy and failover)
- **Features**: IP address management, device inventory, network documentation
- **Integration**: Automated subnet generation for DHCP services

#### 🔧 Network Device Management
- **Oxidized**: PROXMOX-NODE-02 (Configuration backup and version control)
- **Features**: Multi-vendor device support, automated backups, change tracking
- **Coverage**: Routers, switches, firewalls, wireless controllers

### 🔐 Authentication Services

#### 🔐 FreeRADIUS
- **Purpose**: Network access authentication (802.1X, WiFi, VPN)
- **Features**: LDAP integration, accounting, policy enforcement
- **Database**: MySQL backend for user and session tracking

#### 🏢 OpenLDAP Directory
- **Purpose**: Centralized user and group management  
- **Features**: LDAP directory services, authentication backend
- **Integration**: FreeRADIUS, system authentication, applications

### 📡 Wireless & ISP Management

#### 📡 UniFi Controller
- **Location**: PROXMOX-NODE-02
- **Purpose**: Wireless infrastructure management
- **Features**: Access point management, guest networks, analytics
- **Coverage**: Enterprise wireless networks and guest access

#### 🌍 UISP Platform
- **Location**: PROXMOX-NODE-01  
- **Purpose**: ISP operations and service provider management
- **Features**: Network planning, service provisioning, customer management
- **Integration**: Network infrastructure and billing systems

### 🛠️ Operational Services

#### 📁 FTP Services
- **Purpose**: File transfer and storage services
- **Features**: Secure FTP, user management, access controls
- **Integration**: Authentication via LDAP/FreeRADIUS

#### ⚡ Firmware Management
- **Location**: PROXMOX-NODE-02
- **Purpose**: Centralized firmware upgrade orchestration
- **Features**: Version tracking, automated deployment, rollback capabilities
- **Coverage**: Network devices, servers, IoT equipment

#### 🖥️ Server Management
- **Purpose**: Linux server lifecycle management and monitoring
- **Features**: Automated updates, configuration management, health monitoring
- **Tools**: Ansible automation, monitoring integration

#### 🖥️ Jump Host Services
- **Location**: PROXMOX-NODE-02
- **Purpose**: Secure access point for administrative tasks
- **Features**: SSH bastion, secure tunneling, audit logging
- **Security**: Multi-factor authentication, session recording

## 🗄️ Database Architecture

### Database Distribution Strategy

The platform uses a distributed database architecture optimized for service isolation, performance, and reliability:

#### PostgreSQL Databases
- **Kea DHCP Primary**: PostgreSQL on dhcp-primary (lease tracking, statistics)
- **Kea DHCP Secondary**: PostgreSQL on dhcp-secondary (HA lease replication)
- **NetBox Primary**: PostgreSQL on NetBox primary (IPAM/DCIM data)
- **NetBox Backup**: PostgreSQL on NetBox backup (synchronized replica)

#### MySQL Databases  
- **FreeRADIUS**: MySQL on FreeRADIUS server (user data, accounting)
- **Other Services**: MySQL databases as required by individual services

#### Database Backup Strategy
- **Automated Backups**: Daily PostgreSQL/MySQL dumps
- **Cross-Node Replication**: Critical data replicated across Proxmox nodes
- **Point-in-Time Recovery**: Transaction log archiving for PostgreSQL
- **Configuration Backups**: Database schemas versioned in git

## ⚙️ Service Deployment Architecture

### Service Distribution by Node

#### PROXMOX-NODE-01 Services
| Service | VM Name | Purpose | Resource Allocation |
|---------|---------|---------|-------------------|
| BIND9 DNS | node01-dns-secondary | Secondary DNS server | 2 CPU, 2048 MB |
| Grafana | node01-grafana | Visualization platform | 2 CPU, 4096 MB |
| NetBox | node01-netbox-backup | Backup IPAM/DCIM | 4 CPU, 4096 MB |
| UISP | node01-uisp | ISP management | 2 CPU, 4096 MB |

#### PROXMOX-NODE-02 Services  
| Service | VM Name | Purpose | Resource Allocation |
|---------|---------|---------|-------------------|
| BIND9 DNS | node01-dns-primary | Primary DNS server | 2 CPU, 2048 MB |
| NetBox | node02-netbox-primary | Primary IPAM/DCIM | 4 CPU, 4096 MB |
| Oxidized | node02-oxidized | Config backup | 2 CPU, 8192 MB |
| Jump Host | node02-jumphost | Admin access point | 2 CPU, 8192 MB |
| UniFi | node02-unifi | Wireless controller | 2 CPU, 4096 MB |
| Firmware Mgmt | node02-firmware-mgmt | Firmware orchestration | 2 CPU, 4096 MB |

### Service Communication Patterns

#### High Availability Services
```
DNS: Primary (PROX02) ←→ Secondary (PROX01)
NetBox: Primary (PROX02) ←→ Backup (PROX01)  
DHCP: Primary (External) ←→ Secondary (External)
```

#### Monitoring Data Flow
```
Infrastructure → Monitoring Agents → Monitoring Platform → Grafana
                                            ↓
                                      Database Backend
```

#### Network Service Integration
```
NetBox IPAM → DHCP Subnets → DNS Zones → Monitoring Discovery
     ↓              ↓             ↓              ↓
Device Inventory → Oxidized → Config Backup → Change Tracking
```

## 🔧 Service Access Information

### Web Interface Access Points

#### Core Management Interfaces
- **NetBox IPAM**: `http://node02-netbox-primary/` (Primary)
- **NetBox IPAM**: `http://node01-netbox-backup/` (Backup)
- **Grafana Dashboards**: `http://node01-grafana:3000/`
- **UniFi Controller**: `https://node02-unifi:8443/`
- **UISP Platform**: `https://node01-uisp/`

#### API Endpoints
- **NetBox API**: `http://node02-netbox-primary/api/`
- **Kea DHCP API**: `http://dhcp-primary:8000/` (Primary)
- **Kea DHCP API**: `http://dhcp-secondary:8000/` (Secondary)
- **Grafana API**: `http://node01-grafana:3000/api/`

### SSH Administrative Access

#### Direct Server Access
```bash
# DNS Servers
ssh ubuntu@node01-dns-primary  # Primary DNS
ssh ubuntu@node01-dns-secondary  # Secondary DNS

# Monitoring Infrastructure  
ssh ubuntu@monitoring-server   # Zabbix Server
ssh ubuntu@monitoring-proxy-01  # Zabbix Proxy 1
ssh ubuntu@monitoring-proxy-02  # Zabbix Proxy 2

# Network Management
ssh ubuntu@node02-netbox-primary  # NetBox Primary
ssh ubuntu@node01-netbox-backup  # NetBox Backup  
ssh ubuntu@node02-oxidized  # Oxidized Config Backup

# Service Platforms
ssh ubuntu@node01-grafana   # Grafana
ssh ubuntu@node02-unifi  # UniFi Controller
ssh ubuntu@node01-uisp   # UISP Platform

# Administrative Services
ssh ubuntu@node02-jumphost  # Jump Host
ssh ubuntu@node02-firmware-mgmt  # Firmware Management
```

#### Jump Host Access (Recommended)
```bash
# Connect via secure jump host
ssh ubuntu@node02-jumphost

# From jump host, access other services
ssh ubuntu@node01-grafana
ssh ubuntu@node02-netbox-primary
```

## 🚀 Deployment Strategy

### Infrastructure as Code Implementation

#### Terraform Infrastructure Management
- **VM Provisioning**: Individual Terraform modules per service
- **Configuration**: Service-specific terraform.tfvars files
- **State Management**: Distributed state files per deployment
- **Versioning**: Git-based infrastructure versioning

#### Ansible Service Automation  
- **Service Deployment**: Standardized playbooks per service
- **Configuration Management**: Environment-specific inventories
- **Health Monitoring**: Automated health check playbooks
- **Lifecycle Management**: Deploy, update, backup, recover workflows

#### Deployment Environments
```
├── Production Deployment
│   ├── terraform/PROXMOX-NODE-01/     # Production node 1 VMs
│   ├── terraform/PROXMOX-NODE-02/     # Production node 2 VMs  
│   └── ansible/*/inventories/production/
│
├── Lab Environment
│   ├── terraform/example/           # Template configurations
│   └── ansible/*/inventories/lab/   # Lab-specific settings
│
└── Development Environment
    ├── .devcontainer/               # VS Code development
    └── docker-compose.yml           # Local testing
```

### Resource Allocation Summary

#### PROXMOX-NODE-01 Resources
- **Total VMs**: 7 virtual machines
- **Total CPU**: 18 cores allocated  
- **Total Memory**: 30 GB RAM allocated
- **Storage**: local-lvm backend
- **Network**: vmbr0 bridge, VLAN 150

#### PROXMOX-NODE-02 Resources
- **Total VMs**: 6 virtual machines
- **Total CPU**: 16 cores allocated
- **Total Memory**: 32 GB RAM allocated  
- **Storage**: local-lvm backend
- **Network**: vmbr0 bridge, VLAN 150

## 🔍 Health Monitoring & Operations

### Automated Health Monitoring

#### Service-Level Health Checks
```bash
# DNS Services Health
cd ansible/bind9
ansible-playbook -i inventories/production/hosts.yml authoritative_health_check.yml
ansible-playbook -i inventories/production/hosts.yml recursive_health_check.yml

# DHCP Services Health  
cd ansible/kea_dhcp
ansible-playbook -i inventories/production/hosts.yml health_check.yml

# Monitoring Infrastructure Health
cd ansible/zabbix
ansible-playbook -i inventories/production/hosts.yml server_health_check.yml
ansible-playbook -i inventories/production/hosts.yml proxy_health_check.yml

# Network Management Health
cd ansible/netbox
ansible-playbook -i inventories/production/hosts.yml health_check.yml
```

#### Infrastructure Connectivity Tests
```bash
# Web Interface Availability
curl -I http://node02-netbox-primary/         # NetBox
curl -I http://node01-grafana:3000/    # Grafana
curl -I http://monitoring-server/zabbix  # Zabbix

# API Endpoint Tests
curl -s http://node02-netbox-primary/api/ | jq '.api_version'
curl -X POST http://dhcp-primary:8000/ \
  -d '{"command": "list-commands", "service": ["dhcp4"]}'
```

### Comprehensive Platform Monitoring

#### Multi-Service Status Dashboard
```bash
# Platform-wide health check script
cat > scripts/platform_health.sh << 'EOF'
#!/bin/bash
echo "=== Platform Health Check ==="
date

# Check core services
services=("node01-dns-primary" "node02-netbox-primary" "node01-grafana" 
          "monitoring-server" "dhcp-primary")

for service in "${services[@]}"; do
    echo "Checking $service..."
    if ping -c1 $service >/dev/null 2>&1; then
        echo "✓ $service: Network OK"
    else  
        echo "✗ $service: Network FAILED"
    fi
done

# Check web interfaces
web_services=("node02-netbox-primary" "node01-grafana:3000" "monitoring-server/zabbix")
for web in "${web_services[@]}"; do
    if curl -sf "http://$web" >/dev/null; then
        echo "✓ $web: Web interface OK"
    else
        echo "✗ $web: Web interface FAILED"  
    fi
done
EOF

chmod +x scripts/platform_health.sh
./scripts/platform_health.sh
```

## 📊 Platform Capacity & Scaling

### Current Platform Capacity

#### Service Capacity Estimates
- **DNS Queries**: 10,000+ queries/second (combined primary/secondary)
- **DHCP Leases**: 50,000+ concurrent leases across subnets
- **NetBox Objects**: 100,000+ IP addresses, devices, and circuits
- **Monitoring Points**: 500,000+ metrics across all Zabbix proxies
- **Configuration Backups**: 1,000+ network devices via Oxidized
- **Concurrent Users**: 200+ simultaneous web interface users

#### Resource Utilization Targets
- **CPU Usage**: Target 60% average, 80% peak
- **Memory Usage**: Target 70% average, 85% peak  
- **Database Size**: PostgreSQL ~50GB, MySQL ~100GB
- **Network Throughput**: 1Gbps per node sustained

### Horizontal Scaling Strategy

#### Service Expansion Patterns
```bash
# Add new monitoring proxy
cd terraform/PROXMOX-NODE-01/ab-thn-nxg-zabbix-proxy03
terraform apply

# Deploy additional DHCP server
cd ansible/kea_dhcp
# Add new server to inventory
ansible-playbook -i inventories/production/hosts.yml deploy_server.yml

# Scale DNS infrastructure
cd terraform/PROXMOX-NODE-01/ab-thn-nxg-bind03
terraform apply
```

#### Geographic Distribution
- **Regional Proxies**: Deploy Zabbix proxies in remote locations
- **DHCP Relay**: Configure DHCP relay agents for remote subnets  
- **DNS Anycast**: Implement DNS anycast for global load distribution
- **Oxidized Scaling**: Multiple Oxidized instances for device segmentation

### Vertical Scaling Guidelines

#### Resource Scaling Triggers
- **CPU**: Scale up when sustained >80% for monitoring services
- **Memory**: Scale up when >85% for database-heavy services  
- **Storage**: Scale up when >75% for log-intensive services
- **Network**: Scale up when >70% sustained throughput

#### Scaling Recommendations by Service
```bash
# High-load NetBox scaling
vm_memory = 16384  # Scale from 4GB to 16GB
vm_cores  = 8      # Scale from 4 to 8 cores

# Database-intensive Zabbix scaling  
vm_memory = 32768  # Scale from 8GB to 32GB
vm_cores  = 16     # Scale from 4 to 16 cores

# High-throughput DHCP scaling
vm_memory = 8192   # Scale from 2GB to 8GB
vm_cores  = 6      # Scale from 2 to 6 cores
```

## 🛠️ Maintenance & Operations

### Automated Maintenance Procedures

#### Regular Maintenance Automation
```bash
# Weekly maintenance routine
cat > scripts/weekly_maintenance.sh << 'EOF'
#!/bin/bash
echo "=== Weekly Platform Maintenance ==="

# System updates (all services)
cd ansible/server_management
ansible-playbook -i inventories/production/hosts.yml deploy.yml --tags updates

# Database maintenance
cd ansible/kea_dhcp
ansible-playbook -i inventories/production/hosts.yml maintenance.yml --tags database

cd ansible/zabbix  
ansible-playbook -i inventories/production/hosts.yml maintenance.yml --tags database

# Configuration backup
cd ansible/oxidized
ansible-playbook -i inventories/production/hosts.yml backup_configs.yml

# Health check validation
./scripts/platform_health.sh

echo "Maintenance completed: $(date)"
EOF
```

#### Service-Specific Maintenance
- **DNS**: Weekly zone file validation and cleanup
- **DHCP**: Daily lease database optimization  
- **NetBox**: Weekly database vacuum and reindex
- **Zabbix**: Daily housekeeping and trend cleanup
- **Oxidized**: Daily configuration backup validation

### Comprehensive Backup Strategy

#### Multi-Tier Backup Architecture
```bash
# Tier 1: Real-time configuration backup
cd ansible/oxidized
ansible-playbook -i inventories/production/hosts.yml backup_configs.yml  # Network configs

# Tier 2: Daily service backups  
# Database backups
cd ansible/kea_dhcp
ansible-playbook -i inventories/production/hosts.yml backup.yml

# Tier 3: Weekly VM snapshots
# Proxmox VM snapshots (automated via Proxmox scheduler)

# Tier 4: Monthly full system backup
# Complete infrastructure state backup
```

#### Disaster Recovery Procedures
```bash
# Service recovery workflow
cd ansible/SERVICE_NAME

# 1. Stop affected services  
ansible-playbook -i inventories/production/hosts.yml stop_services.yml

# 2. Restore from backup
ansible-playbook -i inventories/production/hosts.yml restore.yml

# 3. Validate recovery
ansible-playbook -i inventories/production/hosts.yml health_check.yml

# 4. Resume normal operations
ansible-playbook -i inventories/production/hosts.yml start_services.yml
```

### Platform Evolution and Upgrades

#### Service Lifecycle Management
- **Deployment**: Terraform + Ansible automated deployment
- **Configuration**: Git-versioned configuration management
- **Updates**: Rolling updates with health validation
- **Scaling**: Dynamic resource allocation based on metrics
- **Retirement**: Graceful service decommissioning with data migration

#### Technology Stack Evolution
- **Container Migration**: Gradual containerization of stateless services
- **Kubernetes Integration**: Future container orchestration platform
- **API Automation**: Enhanced REST API integrations
- **Observability**: Advanced logging and tracing implementation

---

## 📚 Additional Resources

### Documentation
- **[VM Deployment Guide](VM_DEPLOYMENT_GUIDE.md)**: Comprehensive VM deployment instructions
- **[Service Management Guide](SERVICE_MANAGEMENT_GUIDE.md)**: Complete service lifecycle management
- **[Quick Reference](QUICK_REFERENCE.md)**: Common commands and access information

### Automation
- **Terraform Modules**: Reusable infrastructure components
- **Ansible Roles**: Service-specific automation roles  
- **Health Checks**: Automated monitoring and validation
- **CI/CD Integration**: Automated testing and deployment pipelines

### Support
- **Documentation Updates**: `python3 scripts/generate-docs.py`
- **Infrastructure Validation**: `make validate`
- **Service Health Checks**: Service-specific health check playbooks
- **Community**: Internal knowledge base and runbooks

---

*This document reflects the current enterprise infrastructure platform state.*  
*Generated: 2025-10-30*  
*Platform Version: Multi-Service Enterprise Infrastructure v2.0*  
*Total Services: 15+ enterprise services across 2 Proxmox nodes*
