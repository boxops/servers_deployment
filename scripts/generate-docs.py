#!/usr/bin/env python3
"""
Infrastructure Documentation Generator

This script dynamically generates architectural documentation based on the current
Terraform and Ansible configuration, creating user-friendly documentation that
reflects the actual deployed infrastructure.

Usage:
    python3 scripts/generate-docs.py [options]

Options:
    --config-dir PATH    Path to terraform directory (default: ./terraform)
    --ansible-dir PATH   Path to ansible directory (default: ./ansible)
    --output-dir PATH    Output directory for generated docs (default: ./docs)
    --format FORMAT      Output format: markdown, html (default: markdown)
    --validate           Validate infrastructure before generating docs
"""

import os
import sys
import json
import yaml
import argparse
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional


class InfrastructureDocsGenerator:
    def __init__(self, config_dir: str, ansible_dir: str, output_dir: str):
        self.config_dir = Path(config_dir)
        self.ansible_dir = Path(ansible_dir)
        self.output_dir = Path(output_dir)
        self.terraform_vars = {}
        self.ansible_vars = {}
        self.infrastructure = {}

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def load_terraform_config(self) -> Dict[str, Any]:
        """Load Terraform configuration and variables."""
        print("📋 Loading Terraform configuration...")

        # Load terraform.tfvars
        tfvars_file = self.config_dir / "terraform.tfvars"
        if tfvars_file.exists():
            self.terraform_vars = self._parse_tfvars(tfvars_file)

        # Load Terraform outputs if available
        try:
            result = subprocess.run(
                ["terraform", "output", "-json"],
                cwd=self.config_dir,
                capture_output=True,
                text=True,
                check=True,
            )
            terraform_outputs = json.loads(result.stdout)
            self.terraform_vars.update(
                {k: v.get("value", "") for k, v in terraform_outputs.items()}
            )
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            print(
                "⚠️  Could not load Terraform outputs (not yet applied or terraform not available)"
            )

        return self.terraform_vars

    def _parse_tfvars(self, tfvars_file: Path) -> Dict[str, Any]:
        """Parse Terraform variables file."""
        vars_dict = {}

        with open(tfvars_file, "r") as f:
            content = f.read()

        # Remove comments and parse key-value pairs
        lines = content.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("\"'")
                vars_dict[key] = value

        return vars_dict

    def load_ansible_config(self) -> Dict[str, Any]:
        """Load Ansible configuration and inventory."""
        print("📋 Loading Ansible configuration...")

        # Load inventory
        inventory_file = self.ansible_dir / "inventories" / "hosts.yml"
        if inventory_file.exists():
            with open(inventory_file, "r") as f:
                inventory = yaml.safe_load(f)
                self.ansible_vars["inventory"] = inventory

        # Load group variables
        group_vars_dir = self.ansible_dir / "group_vars"
        if group_vars_dir.exists():
            for var_file in group_vars_dir.glob("*.yml"):
                with open(var_file, "r") as f:
                    group_vars = yaml.safe_load(f)
                    self.ansible_vars[var_file.stem] = group_vars

        return self.ansible_vars

    def analyze_infrastructure(self) -> Dict[str, Any]:
        """Analyze and categorize infrastructure components."""
        print("🔍 Analyzing infrastructure...")

        infrastructure = {
            "servers": [],
            "proxies": [],
            "network": {},
            "resources": {},
            "services": [],
            "deployment_info": {},
        }

        # Extract server information
        if "inventory" in self.ansible_vars:
            inventory = self.ansible_vars["inventory"]

            # Zabbix Servers
            if "all" in inventory and "children" in inventory["all"]:
                zabbix_config = inventory["all"]["children"].get("zabbix", {})

                # Process servers
                servers = (
                    zabbix_config.get("children", {})
                    .get("zabbix_servers", {})
                    .get("hosts", {})
                )
                for node_name, config in servers.items():
                    server_info = {
                        "name": node_name,
                        "hostname": config.get("ansible_host", "Unknown"),
                        "role": "Zabbix Server",
                        "description": "Primary Zabbix server with web interface and database",
                        "ip_address": config.get("ansible_host"),
                        "database": {
                            "host": config.get("zabbix_server_dbhost", "localhost"),
                            "name": config.get("zabbix_server_dbname", "zabbix"),
                            "user": config.get("zabbix_server_dbuser", "zabbix"),
                        },
                        "services": [
                            "Zabbix Server",
                            "MySQL Database",
                            "Apache Web Server",
                        ],
                        "vm_id": self.terraform_vars.get(
                            "zabbix_server_vmid", "Unknown"
                        ),
                        "cpu_cores": self.terraform_vars.get(
                            "zabbix_server_cores", "Unknown"
                        ),
                        "memory_mb": self.terraform_vars.get(
                            "zabbix_server_memory", "Unknown"
                        ),
                    }
                    infrastructure["servers"].append(server_info)

                # Process proxies
                proxies = (
                    zabbix_config.get("children", {})
                    .get("zabbix_proxies", {})
                    .get("hosts", {})
                )
                proxy_count = 1
                for node_name, config in proxies.items():
                    proxy_info = {
                        "name": node_name,
                        "hostname": config.get("ansible_host", "Unknown"),
                        "role": f"Zabbix Proxy {proxy_count}",
                        "description": f"Zabbix proxy for distributed monitoring (Proxy {proxy_count})",
                        "ip_address": config.get("ansible_host"),
                        "server_connection": config.get("zabbix_proxy_server"),
                        "database": {
                            "host": config.get("zabbix_proxy_dbhost", "localhost"),
                            "name": config.get(
                                "zabbix_proxy_dbname",
                                f'zabbix_proxy{proxy_count if proxy_count > 1 else ""}',
                            ),
                            "user": config.get(
                                "zabbix_proxy_dbuser",
                                f'zabbix_proxy{proxy_count if proxy_count > 1 else ""}',
                            ),
                        },
                        "services": ["Zabbix Proxy", "MySQL Database", "Zabbix Agent"],
                        "vm_id": self.terraform_vars.get(
                            f'zabbix_proxy{"2" if proxy_count > 1 else ""}_vmid',
                            "Unknown",
                        ),
                        "cpu_cores": self.terraform_vars.get(
                            f'zabbix_proxy{"2" if proxy_count > 1 else ""}_cores',
                            "Unknown",
                        ),
                        "memory_mb": self.terraform_vars.get(
                            f'zabbix_proxy{"2" if proxy_count > 1 else ""}_memory',
                            "Unknown",
                        ),
                    }
                    infrastructure["proxies"].append(proxy_info)
                    proxy_count += 1

        # Network configuration
        infrastructure["network"] = {
            "gateway": self.terraform_vars.get("network_gateway", "Unknown"),
            "cidr": self.terraform_vars.get("network_cidr", "Unknown"),
            "bridge": self.terraform_vars.get("proxmox_bridge", "vmbr0"),
        }

        # Resource summary
        total_servers = len(infrastructure["servers"])
        total_proxies = len(infrastructure["proxies"])
        total_cpu = 0
        total_memory = 0

        for server in infrastructure["servers"]:
            if (
                isinstance(server["cpu_cores"], (int, str))
                and str(server["cpu_cores"]).isdigit()
            ):
                total_cpu += int(server["cpu_cores"])
            if (
                isinstance(server["memory_mb"], (int, str))
                and str(server["memory_mb"]).isdigit()
            ):
                total_memory += int(server["memory_mb"])

        for proxy in infrastructure["proxies"]:
            if (
                isinstance(proxy["cpu_cores"], (int, str))
                and str(proxy["cpu_cores"]).isdigit()
            ):
                total_cpu += int(proxy["cpu_cores"])
            if (
                isinstance(proxy["memory_mb"], (int, str))
                and str(proxy["memory_mb"]).isdigit()
            ):
                total_memory += int(proxy["memory_mb"])

        infrastructure["resources"] = {
            "total_vms": total_servers + total_proxies,
            "total_cpu_cores": total_cpu,
            "total_memory_gb": round(total_memory / 1024, 1) if total_memory else 0,
            "proxmox_node": self.terraform_vars.get("proxmox_node", "Unknown"),
            "storage": self.terraform_vars.get("proxmox_storage", "local-lvm"),
            "vm_template": self.terraform_vars.get("vm_template", "Unknown"),
        }

        # Services summary
        infrastructure["services"] = [
            "Zabbix Server 7.0",
            "MySQL Database Server",
            "Apache Web Server",
            "Zabbix Proxy (Active Mode)",
            "Zabbix Agent",
        ]

        # Deployment information
        infrastructure["deployment_info"] = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "terraform_dir": str(self.config_dir),
            "ansible_dir": str(self.ansible_dir),
            "proxmox_api": self.terraform_vars.get("proxmox_api_url", "Unknown"),
            "infrastructure_as_code": True,
            "automation_tools": ["Terraform", "Ansible"],
        }

        self.infrastructure = infrastructure
        return infrastructure

    def generate_architecture_markdown(self) -> str:
        """Generate comprehensive architecture documentation in Markdown format."""
        print("📝 Generating architecture documentation...")

        infra = self.infrastructure

        # Calculate network details
        try:
            gateway = infra["network"]["gateway"]
            cidr = infra["network"]["cidr"]
            network_base = ".".join(gateway.split(".")[:-1]) + ".0"
            network_range = f"{network_base}/{cidr}"
        except:
            network_range = "Unknown"

        doc = f"""# Zabbix Infrastructure Architecture

*Generated on {infra['deployment_info']['generated_at']}*

## 🏗️ Architecture Overview

This document describes the current Zabbix monitoring infrastructure deployed using Infrastructure as Code (IaC) principles with Terraform and Ansible.

### Infrastructure Summary
- **Total VMs**: {infra['resources']['total_vms']}
- **Total CPU Cores**: {infra['resources']['total_cpu_cores']}
- **Total Memory**: {infra['resources']['total_memory_gb']} GB
- **Proxmox Node**: {infra['resources']['proxmox_node']}
- **VM Template**: {infra['resources']['vm_template']}
- **Network**: {network_range}

## 🌐 Network Architecture

```
Network: {network_range}
Gateway: {infra['network']['gateway']}
Bridge: {infra['network']['bridge']}

┌─────────────────────────────────────────────────────────────┐
│                    Network Topology                         │
├─────────────────────────────────────────────────────────────┤"""

        # Add servers to network diagram
        for server in infra["servers"]:
            doc += f"""
│ {server['role']} ({server['name']})
│ ├── IP: {server['ip_address']}
│ ├── VM ID: {server['vm_id']}
│ ├── Resources: {server['cpu_cores']} CPU, {server['memory_mb']} MB RAM
│ └── Services: {', '.join(server['services'])}"""

        # Add proxies to network diagram
        for proxy in infra["proxies"]:
            doc += f"""
│ {proxy['role']} ({proxy['name']})
│ ├── IP: {proxy['ip_address']}
│ ├── VM ID: {proxy['vm_id']}
│ ├── Resources: {proxy['cpu_cores']} CPU, {proxy['memory_mb']} MB RAM
│ ├── Connects to: {proxy['server_connection']}
│ └── Services: {', '.join(proxy['services'])}"""

        doc += """
└─────────────────────────────────────────────────────────────
```

## 🖥️ Virtual Machine Details

"""

        # Detailed server information
        for server in infra["servers"]:
            doc += f"""### {server['role']} ({server['name']})

**Purpose**: {server['description']}

| Attribute | Value |
|-----------|-------|
| **IP Address** | {server['ip_address']} |
| **VM ID** | {server['vm_id']} |
| **CPU Cores** | {server['cpu_cores']} |
| **Memory** | {server['memory_mb']} MB |
| **Database Host** | {server['database']['host']} |
| **Database Name** | {server['database']['name']} |
| **Database User** | {server['database']['user']} |
| **Web Interface** | http://{server['ip_address']}/zabbix |
| **Services** | {', '.join(server['services'])} |

**Key Features**:
- Primary Zabbix monitoring server
- Web-based management interface
- MySQL database backend
- API endpoint for automation
- Administrative console access

---

"""

        # Detailed proxy information
        for proxy in infra["proxies"]:
            doc += f"""### {proxy['role']} ({proxy['name']})

**Purpose**: {proxy['description']}

| Attribute | Value |
|-----------|-------|
| **IP Address** | {proxy['ip_address']} |
| **VM ID** | {proxy['vm_id']} |
| **CPU Cores** | {proxy['cpu_cores']} |
| **Memory** | {proxy['memory_mb']} MB |
| **Server Connection** | {proxy['server_connection']} |
| **Database Host** | {proxy['database']['host']} |
| **Database Name** | {proxy['database']['name']} |
| **Database User** | {proxy['database']['user']} |
| **Services** | {', '.join(proxy['services'])} |

**Key Features**:
- Active proxy mode (connects to server)
- Local data collection and caching
- Reduced network traffic to main server
- Independent database for local storage
- Automatic failover capabilities

---

"""

        # Database architecture
        doc += f"""## 🗄️ Database Architecture

### Database Distribution
Each component has its own dedicated MySQL database for optimal performance and data isolation:

"""

        # Database details for servers
        for server in infra["servers"]:
            doc += f"""#### {server['role']} Database
- **Database Name**: `{server['database']['name']}`
- **Database User**: `{server['database']['user']}`
- **Purpose**: Main Zabbix data storage (configuration, historical data, templates)
- **Schema**: Full Zabbix server schema with all tables
- **Location**: {server['database']['host']} on {server['ip_address']}

"""

        # Database details for proxies
        for proxy in infra["proxies"]:
            doc += f"""#### {proxy['role']} Database
- **Database Name**: `{proxy['database']['name']}`
- **Database User**: `{proxy['database']['user']}`
- **Purpose**: Proxy data cache and local storage
- **Schema**: Proxy-specific schema for data forwarding
- **Location**: {proxy['database']['host']} on {proxy['ip_address']}

"""

        # Service architecture
        doc += f"""## ⚙️ Service Architecture

### Zabbix Services Deployment

| Service | Location | Purpose | Status Check |
|---------|----------|---------|--------------|"""

        for server in infra["servers"]:
            doc += f"""
| Zabbix Server | {server['ip_address']} | Core monitoring engine | `systemctl status zabbix-server` |
| MySQL Database | {server['ip_address']} | Data storage | `systemctl status mysql` |
| Apache Web Server | {server['ip_address']} | Web interface | `systemctl status apache2` |"""

        for proxy in infra["proxies"]:
            doc += f"""
| Zabbix Proxy | {proxy['ip_address']} | Distributed monitoring | `systemctl status zabbix-proxy` |
| MySQL Database | {proxy['ip_address']} | Proxy data storage | `systemctl status mysql` |
| Zabbix Agent | {proxy['ip_address']} | Self-monitoring | `systemctl status zabbix-agent` |"""

        # Communication flow
        doc += f"""

### Communication Flow

```
Monitored Hosts → Zabbix Proxy → Zabbix Server → Web Interface
                                      ↓
                               MySQL Database
```

1. **Data Collection**: Monitored hosts send data to assigned Zabbix Proxy
2. **Data Forwarding**: Proxy forwards aggregated data to Zabbix Server
3. **Data Storage**: Server stores data in MySQL database
4. **Data Presentation**: Web interface queries database for visualization

## 🔧 Access Information

### Web Interface Access
"""

        for server in infra["servers"]:
            doc += f"""- **Zabbix Web UI**: http://{server['ip_address']}/zabbix
- **Default Credentials**: Admin / zabbix (⚠️ Change immediately)
- **API Endpoint**: http://{server['ip_address']}/zabbix/api_jsonrpc.php
"""

        doc += f"""
### SSH Access
"""

        for server in infra["servers"]:
            doc += f"""- **{server['role']}**: `ssh ubuntu@{server['ip_address']}`
"""

        for proxy in infra["proxies"]:
            doc += f"""- **{proxy['role']}**: `ssh ubuntu@{proxy['ip_address']}`
"""

        doc += f"""
### Proxy Registration

Proxies must be registered in the Zabbix server web interface:

1. Login to Zabbix web interface
2. Navigate to **Administration → Proxies**
3. Click **Create proxy**
4. Configure proxy settings:
"""

        for proxy in infra["proxies"]:
            doc += f"""
   - **Proxy name**: `{proxy['name'].replace('node-', 'zabbix-proxy').replace('3', '2')}`
   - **Proxy mode**: Active
   - **Description**: {proxy['description']}
"""

        # Deployment details
        doc += f"""
## 🚀 Deployment Information

### Infrastructure as Code
This infrastructure is deployed using:
- **Terraform**: VM provisioning and infrastructure management
- **Ansible**: Service configuration and application deployment
- **Proxmox VE**: Virtualization platform

### Configuration Files
- **Terraform Config**: `{infra['deployment_info']['terraform_dir']}`
- **Ansible Config**: `{infra['deployment_info']['ansible_dir']}`
- **Proxmox API**: {infra['deployment_info']['proxmox_api']}

### Resource Allocation
- **Total VMs**: {infra['resources']['total_vms']} virtual machines
- **Total CPU**: {infra['resources']['total_cpu_cores']} cores allocated
- **Total Memory**: {infra['resources']['total_memory_gb']} GB RAM allocated
- **Storage Backend**: {infra['resources']['storage']}
- **Template Used**: {infra['resources']['vm_template']}

## 🔍 Health Monitoring

### Service Health Checks
```bash
# Check all Zabbix services
"""

        for server in infra["servers"]:
            doc += f"""ssh ubuntu@{server['ip_address']} 'sudo systemctl status zabbix-server mysql apache2'
"""

        for proxy in infra["proxies"]:
            doc += f"""ssh ubuntu@{proxy['ip_address']} 'sudo systemctl status zabbix-proxy mysql zabbix-agent'
"""

        doc += f"""
# Check proxy connectivity
"""

        for proxy in infra["proxies"]:
            doc += f"""ssh ubuntu@{proxy['ip_address']} 'sudo tail -n 10 /var/log/zabbix/zabbix_proxy.log'
"""

        doc += f"""```

### Network Connectivity Tests
```bash
# Test web interface
"""

        for server in infra["servers"]:
            doc += f"""curl -I http://{server['ip_address']}/zabbix
"""

        doc += f"""
# Test API connectivity
"""

        for server in infra["servers"]:
            doc += f"""curl -X POST http://{server['ip_address']}/zabbix/api_jsonrpc.php \\
  -H "Content-Type: application/json" \\
  -d '{{"jsonrpc":"2.0","method":"apiinfo.version","params":{{}},"id":1}}'
"""

        doc += f"""```

## 📊 Capacity Planning

### Current Capacity
Based on the current configuration, this infrastructure can handle:

- **Monitored Hosts**: Up to 1,000 hosts per proxy (recommended)
- **Data Points**: ~50,000 values per second (combined)
- **Historical Data**: 30 days default retention
- **Concurrent Users**: 50+ web interface users

### Scaling Recommendations
- **Horizontal Scaling**: Add more proxies for geographic distribution
- **Vertical Scaling**: Increase VM resources for higher load
- **Database Optimization**: Consider dedicated database VMs for large deployments

## 🛠️ Maintenance

### Regular Maintenance Tasks
1. **System Updates**: Monthly OS and Zabbix updates
2. **Database Maintenance**: Weekly database optimization
3. **Log Rotation**: Monitor and rotate log files
4. **Backup Verification**: Test backup and restore procedures
5. **Capacity Monitoring**: Monitor resource usage trends

### Backup Strategy
- **VM Snapshots**: Daily snapshots via Proxmox
- **Database Backups**: Daily MySQL dumps
- **Configuration Backup**: Version control for Terraform/Ansible configs

---

*This document was automatically generated from the current infrastructure configuration.*
*Last updated: {infra['deployment_info']['generated_at']}*
"""

        return doc

    def generate_quick_reference(self) -> str:
        """Generate a quick reference card."""
        infra = self.infrastructure

        ref = f"""# Zabbix Infrastructure Quick Reference

*Generated: {infra['deployment_info']['generated_at']}*

## 🔗 Quick Access Links
"""

        for server in infra["servers"]:
            ref += f"""
- **Zabbix Web Interface**: http://{server['ip_address']}/zabbix
- **SSH to Server**: `ssh ubuntu@{server['ip_address']}`"""

        for proxy in infra["proxies"]:
            ref += f"""
- **SSH to {proxy['role']}**: `ssh ubuntu@{proxy['ip_address']}`"""

        ref += f"""

## 📋 Infrastructure Summary
- **Total VMs**: {infra['resources']['total_vms']}
- **Network**: {infra['network']['gateway'].rsplit('.', 1)[0]}.0/{infra['network']['cidr']}
- **Proxmox Node**: {infra['resources']['proxmox_node']}

## ⚡ Quick Commands
```bash
# Health check all services
"""

        for server in infra["servers"]:
            ref += f"""ssh ubuntu@{server['ip_address']} 'sudo systemctl is-active zabbix-server mysql apache2'
"""

        for proxy in infra["proxies"]:
            ref += f"""ssh ubuntu@{proxy['ip_address']} 'sudo systemctl is-active zabbix-proxy mysql'
"""

        ref += f"""
# View service logs
"""

        for server in infra["servers"]:
            ref += f"""ssh ubuntu@{server['ip_address']} 'sudo journalctl -u zabbix-server -n 20'
"""

        for proxy in infra["proxies"]:
            ref += f"""ssh ubuntu@{proxy['ip_address']} 'sudo journalctl -u zabbix-proxy -n 20'
"""

        ref += f"""
# Restart services if needed
"""

        for server in infra["servers"]:
            ref += f"""ssh ubuntu@{server['ip_address']} 'sudo systemctl restart zabbix-server'
"""

        for proxy in infra["proxies"]:
            ref += f"""ssh ubuntu@{proxy['ip_address']} 'sudo systemctl restart zabbix-proxy'
"""

        ref += f"""```

## 🔧 Troubleshooting
- **Web UI not accessible**: Check Apache service and firewall
- **Proxy not connecting**: Verify proxy registration in web interface
- **Database errors**: Check MySQL service and disk space
- **Performance issues**: Monitor CPU/memory usage on VMs

---
*For detailed architecture information, see [ARCHITECTURE.md](ARCHITECTURE.md)*
"""

        return ref

    def validate_infrastructure(self) -> bool:
        """Validate that infrastructure is accessible and healthy."""
        print("🔍 Validating infrastructure...")

        validation_passed = True

        # Test SSH connectivity
        for server in self.infrastructure["servers"]:
            try:
                result = subprocess.run(
                    [
                        "ssh",
                        "-o",
                        "ConnectTimeout=5",
                        "-o",
                        "StrictHostKeyChecking=no",
                        f"ubuntu@{server['ip_address']}",
                        "echo 'SSH OK'",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    print(f"✅ SSH to {server['role']} ({server['ip_address']}) - OK")
                else:
                    print(
                        f"❌ SSH to {server['role']} ({server['ip_address']}) - FAILED"
                    )
                    validation_passed = False
            except:
                print(f"❌ SSH to {server['role']} ({server['ip_address']}) - FAILED")
                validation_passed = False

        for proxy in self.infrastructure["proxies"]:
            try:
                result = subprocess.run(
                    [
                        "ssh",
                        "-o",
                        "ConnectTimeout=5",
                        "-o",
                        "StrictHostKeyChecking=no",
                        f"ubuntu@{proxy['ip_address']}",
                        "echo 'SSH OK'",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    print(f"✅ SSH to {proxy['role']} ({proxy['ip_address']}) - OK")
                else:
                    print(f"❌ SSH to {proxy['role']} ({proxy['ip_address']}) - FAILED")
                    validation_passed = False
            except:
                print(f"❌ SSH to {proxy['role']} ({proxy['ip_address']}) - FAILED")
                validation_passed = False

        return validation_passed

    def run(self, validate: bool = False) -> None:
        """Run the documentation generation process."""
        print("🚀 Starting Zabbix Infrastructure Documentation Generation")
        print("=" * 60)

        # Load configurations
        self.load_terraform_config()
        self.load_ansible_config()

        # Analyze infrastructure
        self.analyze_infrastructure()

        # Validate if requested
        if validate:
            if not self.validate_infrastructure():
                print(
                    "⚠️  Infrastructure validation failed, but continuing with documentation generation..."
                )
            else:
                print("✅ Infrastructure validation passed")

        # Generate documentation
        architecture_doc = self.generate_architecture_markdown()
        quick_ref = self.generate_quick_reference()

        # Write files
        architecture_file = self.output_dir / "ARCHITECTURE.md"
        quick_ref_file = self.output_dir / "QUICK_REFERENCE.md"

        with open(architecture_file, "w") as f:
            f.write(architecture_doc)

        with open(quick_ref_file, "w") as f:
            f.write(quick_ref)

        print("=" * 60)
        print("📝 Documentation generated successfully!")
        print(f"📄 Architecture documentation: {architecture_file}")
        print(f"🔗 Quick reference: {quick_ref_file}")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Generate Zabbix infrastructure documentation from current configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--config-dir",
        default="./terraform",
        help="Path to terraform directory (default: ./terraform)",
    )

    parser.add_argument(
        "--ansible-dir",
        default="./ansible",
        help="Path to ansible directory (default: ./ansible)",
    )

    parser.add_argument(
        "--output-dir",
        default="./docs",
        help="Output directory for generated docs (default: ./docs)",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate infrastructure connectivity before generating docs",
    )

    args = parser.parse_args()

    # Create generator and run
    generator = InfrastructureDocsGenerator(
        config_dir=args.config_dir,
        ansible_dir=args.ansible_dir,
        output_dir=args.output_dir,
    )

    try:
        generator.run(validate=args.validate)
    except KeyboardInterrupt:
        print("\n⚠️  Documentation generation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error generating documentation: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
