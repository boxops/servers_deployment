# Service Management Guide

**A comprehensive guide for managing services using Ansible - Using Kea DHCP as a practical example**

## Table of Contents

- [🎯 Overview](#overview)
- [📋 Service Architecture](#service-architecture)
- [🚀 Quick Start](#quick-start)
- [🔄 Complete Service Lifecycle](#complete-service-lifecycle)
- [⚙️ Configuration Management](#configuration-management)
- [🔍 Monitoring and Health Checks](#monitoring-and-health-checks)
- [🛠️ Troubleshooting and Recovery](#troubleshooting-and-recovery)
- [🏗️ Advanced Operations](#advanced-operations)
- [📚 Service-Specific Guides](#service-specific-guides)

---

## Overview

This guide demonstrates enterprise-grade service lifecycle management using Ansible automation. While we use **Kea DHCP** as our primary example, the principles and patterns apply to all services in the platform:

- **BIND9 DNS** - Authoritative and recursive DNS services
- **NetBox IPAM** - IP address and data center management
- **Grafana** - Metrics visualization and dashboards
- **FreeRADIUS** - Authentication services
- **Oxidized** - Network device configuration backup
- **And many more...**

### Why Kea DHCP as an Example?

Kea DHCP demonstrates advanced service management patterns:
- **Database Integration**: PostgreSQL backend for lease tracking
- **High Availability**: Master/slave configuration with failover
- **API Integration**: RESTful API for management and monitoring
- **Configuration Complexity**: Multiple configuration files and validation
- **Real-time Operations**: Live configuration updates and monitoring

---

## Service Architecture

### Understanding Service Structure

Every service in the platform follows a standardized structure:

```
ansible/service-name/
├── deploy.yml              # 🚀 Initial service deployment
├── update_config.yml       # 🔄 Configuration updates  
├── health_check.yml        # 💚 Health monitoring
├── ansible.cfg            # ⚙️ Service-specific Ansible settings
├── inventories/           # 🏠 Environment definitions
│   ├── production/
│   │   └── hosts.yml      # Production servers
│   └── lab/
│       └── hosts.yml      # Lab/testing servers
├── roles/                 # 📦 Reusable automation components
│   ├── service-name/      # Main service role
│   └── dependencies/      # Required dependencies (DB, etc.)
├── intended_configs/      # 📄 Desired configuration files
│   ├── server1.service.conf
│   └── server2.service.conf
├── actual_configs/        # 📁 Current server configurations (backups)
├── scripts/              # 🔧 Helper scripts and utilities
└── README.md             # 📖 Service-specific documentation
```

### Kea DHCP Service Architecture

```
ansible/kea_dhcp/
├── deploy_server.yml           # Complete DHCP server deployment
├── update_config.yml           # Deploy configuration changes
├── health_check.yml            # Service health validation
├── diff_config.yml             # Compare intended vs actual configs
├── copy_actual_to_intended.yml # Backup current configurations
├── generate_subnets.yml        # Generate subnets from NetBox
├── log_analysis.yml            # Analyze DHCP logs for issues
├── inventories/
│   ├── production/
│   │   └── hosts.yml           # dhcp-primary, dhcp-secondary
│   └── lab/
│       └── hosts.yml           # Lab DHCP servers
├── roles/
│   ├── kea_dhcp/              # Kea DHCP installation and config
│   └── postgresql/            # PostgreSQL database setup
├── intended_configs/           # Target configurations
│   ├── dhcp-primary.kea-dhcp4.conf
│   ├── dhcp-primary.kea-ctrl-agent.conf
│   ├── dhcp-secondary.kea-dhcp4.conf
│   └── dhcp-secondary.kea-ctrl-agent.conf
├── actual_configs/             # Current server configurations
├── log_analysis_results/       # Log analysis outputs
└── scripts/                    # Automation helpers
```

---

## Quick Start

### Prerequisites

Before managing services, ensure:

- [ ] VMs are deployed and accessible via SSH
- [ ] Ansible is installed with required collections
- [ ] SSH keys are configured for target servers
- [ ] Service-specific requirements are met (databases, etc.)

### Basic Service Operations

```bash
# Navigate to service directory
cd ansible/kea_dhcp

# Deploy complete service
ansible-playbook -i inventories/production/hosts.yml deploy_server.yml

# Check service health
ansible-playbook -i inventories/production/hosts.yml health_check.yml

# Update configurations
ansible-playbook -i inventories/production/hosts.yml update_config.yml

# Analyze service status
ansible-playbook -i inventories/production/hosts.yml log_analysis.yml
```

---

## Complete Service Lifecycle

### Phase 1: Initial Deployment

#### 1.1 Prepare Environment

```bash
# Verify VM connectivity
ansible -i inventories/production/hosts.yml all -m ping

# Check sudo access  
ansible -i inventories/production/hosts.yml all -m shell -a "sudo whoami"

# Verify system resources
ansible -i inventories/production/hosts.yml all -m shell -a "free -h && df -h"
```

#### 1.2 Deploy Service Infrastructure

The `deploy_server.yml` playbook performs complete service deployment:

```bash
ansible-playbook -i inventories/production/hosts.yml deploy_server.yml -v
```

**What happens during deployment:**

1. **System Preparation**
   - Package cache updates
   - Essential package installation
   - System security configuration

2. **Database Setup** (PostgreSQL for Kea DHCP)
   - PostgreSQL installation and configuration
   - Database and user creation
   - Schema initialization

3. **Service Installation**
   - Kea DHCP packages and dependencies
   - Service user and group creation
   - Directory structure creation

4. **Initial Configuration**
   - Base configuration deployment
   - Service registration and enablement
   - Initial service startup

5. **Verification**
   - Service status checks
   - Basic functionality tests
   - Log verification

#### 1.3 Post-Deployment Validation

```bash
# Run comprehensive health checks
ansible-playbook -i inventories/production/hosts.yml health_check.yml

# Verify service-specific functionality
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "systemctl status isc-kea-dhcp4-server"

# Test DHCP port listening
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "ss -lun | grep ':67 '"
```

### Phase 2: Configuration Management

#### 2.1 Understanding Configuration Files

Kea DHCP uses multiple configuration files:

- **kea-dhcp4.conf** - Main DHCP server configuration
- **kea-ctrl-agent.conf** - Control agent for API access
- **PostgreSQL configs** - Database connection settings

#### 2.2 Configuration Update Workflow

```bash
# 1. Edit intended configurations
vim intended_configs/dhcp-primary.kea-dhcp4.conf

# Example configuration changes:
{
  "Dhcp4": {
    "interfaces-config": {
      "interfaces": [ "eth0" ]
    },
    "lease-database": {
      "type": "postgresql",
      "host": "localhost",
      "name": "kea",
      "user": "kea",
      "password": "kea_password"
    },
    "subnet4": [
      {
        "subnet": "10.0.1.0/24",
        "pools": [
          {
            "pool": "10.0.1.X - 10.0.1.200"
          }
        ],
        "option-data": [
          {
            "name": "routers",
            "data": "10.0.1.1"
          },
          {
            "name": "domain-name-servers", 
            "data": "8.8.8.8, 8.8.4.4"
          }
        ]
      }
    ]
  }
}

# 2. Validate configuration locally (optional)
kea-dhcp4 -t intended_configs/dhcp-primary.kea-dhcp4.conf

# 3. Deploy configuration to servers
ansible-playbook -i inventories/production/hosts.yml update_config.yml

# 4. Verify deployment success
ansible-playbook -i inventories/production/hosts.yml health_check.yml
```

#### 2.3 Configuration Validation and Rollback

```bash
# Compare intended vs actual configurations
ansible-playbook -i inventories/production/hosts.yml diff_config.yml

# Create backup of current configurations
ansible-playbook -i inventories/production/hosts.yml copy_actual_to_intended.yml

# Rollback if needed (restore from git)
git checkout HEAD~1 -- intended_configs/
ansible-playbook -i inventories/production/hosts.yml update_config.yml
```

### Phase 3: Ongoing Operations

#### 3.1 Health Monitoring

Regular health monitoring ensures service reliability:

```bash
# Automated health checks (run daily via cron)
ansible-playbook -i inventories/production/hosts.yml health_check.yml

# Service-specific monitoring
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "pgrep -f kea-dhcp4"
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "ss -lun | grep ':67 '"

# Database health  
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "sudo -u postgres psql kea -c 'SELECT COUNT(*) FROM lease4;'"
```

#### 3.2 Log Analysis and Troubleshooting

```bash
# Automated log analysis
ansible-playbook -i inventories/production/hosts.yml log_analysis.yml

# Manual log inspection
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "tail -100 /var/log/kea/kea-dhcp4.log"

# Search for specific issues
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "grep -i 'error\|warning\|failed' /var/log/kea/kea-dhcp4.log | tail -20"

# Check recent DHCP activity
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "grep 'DHCPREQUEST\|DHCPACK\|DHCPNAK' /var/log/kea/kea-dhcp4.log | tail -10"
```

#### 3.3 Performance Monitoring

```bash
# System resource monitoring
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "top -bn1 | head -20"
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "free -h"
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "df -h"

# DHCP lease statistics
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "sudo -u postgres psql kea -c \"
  SELECT 
    subnet_id,
    COUNT(*) as total_leases,
    SUM(CASE WHEN state = 0 THEN 1 ELSE 0 END) as active_leases,
    SUM(CASE WHEN state = 1 THEN 1 ELSE 0 END) as expired_leases
  FROM lease4 
  GROUP BY subnet_id;
\""
```

### Phase 4: Advanced Operations

#### 4.1 High Availability Configuration

Configure DHCP failover between primary and secondary servers:

```json
// In intended_configs/dhcp-primary.kea-dhcp4.conf
{
  "Dhcp4": {
    "hooks-libraries": [
      {
        "library": "/usr/lib/x86_64-linux-gnu/kea/hooks/libdhcp_ha.so",
        "parameters": {
          "high-availability": [
            {
              "this-server-name": "server1",
              "mode": "hot-standby",
              "heartbeat-delay": 10000,
              "max-response-delay": 10000,
              "max-ack-delay": 5000,
              "max-unacked-clients": 5,
              "peers": [
                {
                  "name": "server1",
                  "url": "http://10.0.2.91:8000/",
                  "role": "primary"
                },
                {
                  "name": "server2",
                  "url": "http://10.0.1.91:8000/",
                  "role": "standby"
                }
              ]
            }
          ]
        }
      }
    ]
  }
}
```

#### 4.2 API Integration and Automation

Use Kea's REST API for advanced management:

```bash
# Get DHCP statistics via API
curl -X POST -H "Content-Type: application/json" \
  -d '{"command": "statistic-get-all", "service": ["dhcp4"]}' \
  http://10.0.2.91:8000/

# Reload configuration without service restart
curl -X POST -H "Content-Type: application/json" \
  -d '{"command": "config-reload", "service": ["dhcp4"]}' \
  http://10.0.2.91:8000/

# Get lease information
curl -X POST -H "Content-Type: application/json" \
  -d '{"command": "lease4-get-all", "service": ["dhcp4"]}' \
  http://10.0.2.91:8000/
```

#### 4.3 Integration with NetBox IPAM

Automatically generate DHCP subnets from NetBox:

```bash
# Generate subnets from NetBox
ansible-playbook -i inventories/production/hosts.yml generate_subnets.yml

# Review generated subnet configuration
cat subnet4.json

# Deploy updated configuration with new subnets
ansible-playbook -i inventories/production/hosts.yml update_config.yml
```

---

## Configuration Management

### Configuration File Templates

#### Main DHCP Configuration Template

```json
{
  "Dhcp4": {
    "interfaces-config": {
      "interfaces": [ "{{ dhcp_interface | default('eth0') }}" ]
    },
    "control-socket": {
      "socket-type": "unix",
      "socket-name": "/tmp/kea4-ctrl-socket"
    },
    "lease-database": {
      "type": "postgresql",
      "host": "{{ postgresql_host | default('localhost') }}",
      "name": "{{ postgresql_db | default('kea') }}",
      "user": "{{ postgresql_user | default('kea') }}",
      "password": "{{ postgresql_password }}"
    },
    "hosts-database": {
      "type": "postgresql",
      "host": "{{ postgresql_host | default('localhost') }}",
      "name": "{{ postgresql_db | default('kea') }}",
      "user": "{{ postgresql_user | default('kea') }}",
      "password": "{{ postgresql_password }}"
    },
    "subnet4": {{ dhcp_subnets | to_nice_json }},
    "loggers": [
      {
        "name": "kea-dhcp4",
        "output_options": [
          {
            "output": "/var/log/kea/kea-dhcp4.log",
            "maxsize": 10240000,
            "maxver": 8
          }
        ],
        "severity": "{{ log_level | default('INFO') }}",
        "debuglevel": 0
      }
    ]
  }
}
```

### Environment-Specific Variables

#### Production Variables

```yaml
# inventories/production/group_vars/dhcp_servers.yml
postgresql_password: "secure_production_password"
log_level: "WARN"
dhcp_interface: "eth0"

dhcp_subnets:
  - subnet: "10.0.1.0/24"
    pools:
      - pool: "10.0.1.X - 10.0.1.200"
    option-data:
      - name: "routers"
        data: "10.0.1.1"
      - name: "domain-name-servers"
        data: "8.8.8.8, 8.8.4.4"
      - name: "domain-name"
        data: "example.com"
```

#### Lab Variables

```yaml
# inventories/lab/group_vars/dhcp_servers.yml
postgresql_password: "lab_password"
log_level: "DEBUG"
dhcp_interface: "eth0"

dhcp_subnets:
  - subnet: "10.0.1.0/24"
    pools:
      - pool: "10.0.1.50 - 10.0.1.100"
    option-data:
      - name: "routers"
        data: "10.0.1.1"
      - name: "domain-name-servers"
        data: "10.0.1.1"
```

---

## Monitoring and Health Checks

### Automated Health Monitoring

The `health_check.yml` playbook performs comprehensive service validation:

```yaml
---
- name: Kea DHCP Health Check
  hosts: all
  become: true
  gather_facts: false
  tasks:

    - name: Check Kea DHCP service status
      ansible.builtin.service:
        name: isc-kea-dhcp4-server
        state: started
      register: kea_service
      
    - name: Verify DHCP process running
      ansible.builtin.shell: pgrep -f kea-dhcp4
      register: kea_proc
      changed_when: false
      
    - name: Check DHCP port listening
      ansible.builtin.shell: ss -lun | grep ':67 '
      register: dhcp_port
      changed_when: false
      
    - name: Check PostgreSQL connectivity
      ansible.builtin.shell: sudo -u postgres psql kea -c "SELECT COUNT(*) FROM lease4;"
      register: db_check
      changed_when: false
      
    - name: Analyze recent logs for errors
      ansible.builtin.shell: "grep -i 'error' /var/log/kea/kea-dhcp4.log | tail -n 10"
      register: kea_log_errors
      changed_when: false
      ignore_errors: true
      
    - name: Health check summary
      ansible.builtin.debug:
        msg: |
          Health Check Results:
          - Service Status: {{ kea_service.status.ActiveState }}
          - Process Running: {{ 'YES' if kea_proc.rc == 0 else 'NO' }}
          - Port Listening: {{ 'YES' if dhcp_port.rc == 0 else 'NO' }}
          - Database OK: {{ 'YES' if db_check.rc == 0 else 'NO' }}
          - Recent Errors: {{ kea_log_errors.stdout_lines | length }}
```

### Custom Monitoring Checks

Create service-specific monitoring:

```bash
# Create custom monitoring script
cat > scripts/dhcp_monitor.sh << 'EOF'
#!/bin/bash

# DHCP Service Monitor
# Usage: ./dhcp_monitor.sh [server_ip]

SERVER_IP=${1:-localhost}
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] DHCP Monitor - $SERVER_IP"

# Check service status
systemctl is-active isc-kea-dhcp4-server >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Service: RUNNING"
else
    echo "✗ Service: STOPPED"
    exit 1
fi

# Check port
ss -lun | grep ':67 ' >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✓ Port 67: LISTENING"
else
    echo "✗ Port 67: NOT LISTENING"
    exit 1
fi

# Check recent activity
RECENT_REQUESTS=$(grep "$(date '+%Y-%m-%d %H:')" /var/log/kea/kea-dhcp4.log | grep -c "DHCPREQUEST" || echo "0")
echo "ℹ Recent DHCP requests (current hour): $RECENT_REQUESTS"

# Check database
sudo -u postgres psql kea -c "SELECT COUNT(*) FROM lease4;" >/dev/null 2>&1
if [ $? -eq 0 ]; then
    LEASE_COUNT=$(sudo -u postgres psql kea -t -c "SELECT COUNT(*) FROM lease4;" | tr -d ' ')
    echo "ℹ Current leases: $LEASE_COUNT"
else
    echo "✗ Database: CONNECTION FAILED"
    exit 1
fi

echo "✓ All checks passed"
EOF

chmod +x scripts/dhcp_monitor.sh

# Deploy monitoring script to servers
ansible -i inventories/production/hosts.yml dhcp_servers -m copy -a "src=scripts/dhcp_monitor.sh dest=/usr/local/bin/dhcp_monitor.sh mode=0755"

# Run monitoring checks
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "/usr/local/bin/dhcp_monitor.sh"
```

---

## Troubleshooting and Recovery

### Common Issues and Solutions

#### Service Won't Start

```bash
# Check service status and logs
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "systemctl status isc-kea-dhcp4-server"
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "journalctl -u isc-kea-dhcp4-server -n 50"

# Check configuration syntax
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "kea-dhcp4 -t /etc/kea/kea-dhcp4.conf"

# Common fixes:
# 1. Configuration syntax error - validate config file
# 2. Database connection issue - check PostgreSQL
# 3. Port already in use - check for conflicting services
# 4. File permissions - ensure _kea user can access config files
```

#### Database Connection Issues

```bash
# Test PostgreSQL connectivity
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "sudo -u postgres psql -l"

# Check Kea database exists
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "sudo -u postgres psql -c '\l' | grep kea"

# Recreate database if needed
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "
sudo -u postgres createdb kea
sudo -u postgres psql kea < /usr/share/kea/scripts/pgsql/dhcpdb_create.pgsql
"
```

#### Configuration Issues

```bash
# Compare intended vs actual configuration
ansible-playbook -i inventories/production/hosts.yml diff_config.yml

# Backup current configuration
ansible-playbook -i inventories/production/hosts.yml copy_actual_to_intended.yml

# Restore known-good configuration
git checkout HEAD~1 -- intended_configs/
ansible-playbook -i inventories/production/hosts.yml update_config.yml
```

### Disaster Recovery Procedures

#### Complete Service Recovery

```bash
# 1. Stop services
ansible -i inventories/production/hosts.yml dhcp_servers -m service -a "name=isc-kea-dhcp4-server state=stopped"

# 2. Backup current state
ansible-playbook -i inventories/production/hosts.yml copy_actual_to_intended.yml

# 3. Redeploy from scratch
ansible-playbook -i inventories/production/hosts.yml deploy_server.yml

# 4. Verify recovery
ansible-playbook -i inventories/production/hosts.yml health_check.yml
```

#### Database Recovery

```bash
# Backup existing database
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "sudo -u postgres pg_dump kea > /tmp/kea_backup_$(date +%Y%m%d_%H%M%S).sql"

# Restore database from backup
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "
sudo -u postgres dropdb kea
sudo -u postgres createdb kea  
sudo -u postgres psql kea < /path/to/backup.sql
"

# Restart services
ansible -i inventories/production/hosts.yml dhcp_servers -m service -a "name=isc-kea-dhcp4-server state=restarted"
```

---

## Advanced Operations

### Automated Subnet Management

Integrate with NetBox for dynamic subnet management:

```bash
# Generate subnets from NetBox IPAM
ansible-playbook -i inventories/production/hosts.yml generate_subnets.yml

# This creates subnet4.json with current NetBox subnets
cat subnet4.json | jq '.[0]'  # View first subnet

# Deploy updated configuration
ansible-playbook -i inventories/production/hosts.yml update_config.yml

# Verify subnet deployment
curl -X POST -H "Content-Type: application/json" \
  -d '{"command": "config-get", "service": ["dhcp4"]}' \
  http://10.0.2.91:8000/ | jq '.arguments.Dhcp4.subnet4'
```

### Performance Optimization

#### Database Tuning

```bash
# Optimize PostgreSQL for DHCP workload
ansible -i inventories/production/hosts.yml dhcp_servers -m lineinfile -a "
path=/etc/postgresql/14/main/postgresql.conf
regexp='^#?shared_buffers'
line='shared_buffers = 256MB'
backup=yes
" --become

# Restart PostgreSQL
ansible -i inventories/production/hosts.yml dhcp_servers -m service -a "name=postgresql state=restarted" --become
```

#### Kea Performance Tuning

```json
// Add to kea-dhcp4.conf for high-performance environments
{
  "Dhcp4": {
    "multi-threading": {
      "enable-multi-threading": true,
      "thread-pool-size": 4,
      "packet-queue-size": 64
    },
    "dhcp-ddns": {
      "enable-updates": false
    }
  }
}
```

### Security Hardening

```bash
# Implement security best practices
ansible-playbook -i inventories/production/hosts.yml security_hardening.yml

# Firewall configuration
ansible -i inventories/production/hosts.yml dhcp_servers -m shell -a "
ufw allow from 192.168.0.0/16 to any port 67 proto udp
ufw allow from 192.168.0.0/16 to any port 8000 proto tcp  # Kea API
ufw --force enable
" --become

# File permissions
ansible -i inventories/production/hosts.yml dhcp_servers -m file -a "
path=/etc/kea/
owner=_kea
group=_kea
mode=0750
recurse=yes
" --become
```

---

## Service-Specific Guides

The patterns demonstrated with Kea DHCP apply to all platform services. Here's how to adapt them:

### BIND9 DNS Service

```bash
cd ansible/bind9

# Deploy DNS infrastructure
ansible-playbook -i inventories/hosts.yml deploy.yml

# Update zone files
ansible-playbook -i inventories/hosts.yml zones_update.yml

# Health monitoring
ansible-playbook -i inventories/hosts.yml authoritative_health_check.yml
ansible-playbook -i inventories/hosts.yml recursive_health_check.yml
```

### Zabbix Monitoring

```bash
cd ansible/zabbix

# Deploy monitoring infrastructure
ansible-playbook -i inventories/hosts.yml deploy.yml

# Server and proxy health checks
ansible-playbook -i inventories/hosts.yml server_health_check.yml
ansible-playbook -i inventories/hosts.yml proxy_health_check.yml

# Upgrade procedures
ansible-playbook -i inventories/hosts.yml upgrade.yml
```

### NetBox IPAM

```bash
cd ansible/netbox

# Deploy NetBox platform
ansible-playbook -i inventories/hosts.yml deploy.yml

# Install additional plugins
ansible-playbook -i inventories/hosts.yml install_plugins.yml

# Health monitoring
ansible-playbook -i inventories/hosts.yml health_check.yml
```

### FreeRADIUS Authentication

```bash
cd ansible/freeradius

# Deploy RADIUS infrastructure
ansible-playbook -i inventories/hosts.yml deploy.yml

# Health and connectivity checks
ansible-playbook -i inventories/hosts.yml health_check.yml
```

### Grafana Visualization

```bash
cd ansible/grafana

# Deploy Grafana servers
ansible-playbook -i inventories/hosts.yml deploy.yml

# Configure dashboards and data sources
# (Service-specific configuration management)
```

---

## Best Practices Summary

### Configuration Management
1. **Version Control**: Always commit configuration changes to git
2. **Validation**: Test configurations in lab before production
3. **Backup**: Create backups before major changes
4. **Documentation**: Update service documentation with changes

### Deployment Procedures  
1. **Incremental Rollout**: Deploy to lab → staging → production
2. **Health Checks**: Always run health checks after changes
3. **Rollback Plan**: Have rollback procedures ready
4. **Monitoring**: Implement comprehensive monitoring

### Security Practices
1. **Least Privilege**: Use minimal required permissions
2. **Network Segmentation**: Restrict network access where possible
3. **Regular Updates**: Keep systems and services updated
4. **Audit Logs**: Monitor and audit service access

### Operational Excellence
1. **Automation**: Automate repetitive tasks
2. **Documentation**: Maintain current documentation
3. **Monitoring**: Proactive monitoring and alerting
4. **Training**: Ensure team knowledge transfer

This guide provides the foundation for managing any service in the platform. Adapt the patterns and procedures to your specific service requirements while maintaining consistency across the infrastructure.