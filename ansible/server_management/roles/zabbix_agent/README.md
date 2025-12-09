# zabbix_agent role

This role installs the Zabbix agent (using the official Zabbix repository package) and configures a few key parameters in `/etc/zabbix/zabbix_agentd.conf`.

Configurable variables (defaults are in `defaults/main.yml`):

- `zabbix_agent_install` (bool): whether to install/manage the agent (default: `true`).
- `zabbix_release_deb_url` (string): URL to the zabbix-release .deb that adds the official repo.
- `zabbix_release_deb_name` (string): local filename used when downloading the .deb.
- `zabbix_agent_package` (string): package to install (default: `zabbix-agent`).
- `zabbix_server` (string): value for `Server=` in agent config.
- `zabbix_server_active` (string): value for `ServerActive=` in agent config.
- `zabbix_hostname` (string): value for `Hostname=` in agent config (default: `{{ ansible_fqdn | default(ansible_hostname) }}`).

Usage examples

In a playbook:

---
- hosts: zabbix_clients
  become: yes
  roles:
    - role: server_management/roles/zabbix_agent
      vars:
        zabbix_server: 'zabbix.example.local'
        zabbix_server_active: 'zabbix.example.local:10051'
        zabbix_hostname: '{{ inventory_hostname }}'

You can also override the defaults in `group_vars` or `host_vars`.
