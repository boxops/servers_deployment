from pynetbox import api as NetboxAPI
from zabbix_utils import ZabbixAPI

# from pynautobot import api as Nautobot
import requests

# from pprint import pprint
import ssl
import requests

# Disable SSL warnings
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)

# Disable SSL verification globally
ssl._create_default_https_context = ssl._create_unverified_context


# class NautobotClient:
#     def __init__(self, url, token):
#         self.conn = Nautobot(url=url, token=token, verify=False)

#     def _format_device_data(self, device):
#         """Helper to format device data"""
#         return {
#             "name": device.name,
#             "primary_ip": (
#                 str(device.primary_ip4).split("/")[0] if device.primary_ip4 else None
#             ),
#             "description": device.device_type.display,
#         }

#     def get_device_by_name(self, name):
#         """Retrieve a device by its name"""
#         device = self.conn.dcim.devices.get(name=name)
#         return self._format_device_data(device) if device else None

#     def get_devices(self, status="active"):
#         """Retrieve devices by status from Nautobot"""
#         devices = self.conn.dcim.devices.filter(status=status)
#         return [self._format_device_data(device) for device in devices]

#     def get_devices_by_platform(self, platform):
#         """Retrieve devices by platform from Nautobot"""
#         devices = self.conn.dcim.devices.filter(platform=platform)
#         return [self._format_device_data(device) for device in devices]

#     def graphql_get_devices_by_platform(self, platform):
#         """Retrieve devices by platform from Nautobot using GraphQL"""
#         query = f"""
#         query {{
#             devices(platform: "{platform}") {{
#                 name
#                 primary_ip4 {{
#                     host
#                 }}
#                 device_type {{
#                     model
#                 }}
#             }}
#         }}
#         """
#         response = self.conn.graphql.query(query)
#         devices = response.json["data"]["devices"]
#         return [
#             {
#                 "name": device["name"],
#                 "primary_ip": device["primary_ip4"]["host"] if device["primary_ip4"] else None,
#                 "description": device["device_type"]["model"],
#             }
#             for device in devices
#         ]


class NetBoxClient:
    def __init__(self, url, token):
        self.conn = NetboxAPI(url)
        self.conn.token = token
        self.conn.http_session.verify = False

    def _format_device_data(self, device):
        """Helper to format device data"""
        return {
            "name": device.name,
            "primary_ip": (
                str(device.primary_ip).split("/")[0] if device.primary_ip else None
            ),
            "description": device.device_type.display,
            "snmp_community": self.get_device_custom_field(device, "SNMPCommunity")
            or "your-snmp-community",
            "site": device.site.name if device.site else None,
            "latitude": device.site.latitude if device.site else None,
            "longitude": device.site.longitude if device.site else None,
            "location": device.location.name if device.location else None,
            "manufacturer": (
                device.device_type.manufacturer.name if device.device_type else None
            ),
            "model": device.device_type.model if device.device_type else None,
            "platform": device.platform.name if device.platform else None,
            "role": device.role.name if device.role else None,
            "status": device.status.label if device.status else None,
        }

    def get_device_custom_field(
        self, device, field_name, default="your-snmp-community"
    ):
        """Helper to get custom fields from NetBox devices"""
        return getattr(device, "custom_fields", {}).get(field_name, default)

    def get_device_zabbix_template_name(
        self, device_type, field_name="ZabbixTemplates"
    ):
        """Helper to get custom fields from NetBox device types"""
        return getattr(device_type, "custom_fields", {}).get(field_name, None)

    def get_device_zabbix_monitoring_type(
        self, device_type, field_name="ZabbixMonitoringType"
    ):
        """Helper to get custom fields from NetBox device types"""
        return getattr(device_type, "custom_fields", {}).get(field_name, None)

    def get_device_by_name(self, name):
        """Retrieve a device by its name"""
        device = self.conn.dcim.devices.get(name=name)
        return self._format_device_data(device) if device else None

    def get_devices(self, status="active"):
        """Retrieve devices by status from NetBox"""
        devices = self.conn.dcim.devices.filter(status=status)
        return [self._format_device_data(device) for device in devices]

    def get_devices_by_platform(self, platform):
        """Retrieve devices by platform from NetBox"""
        devices = self.conn.dcim.devices.filter(platform=platform)
        return [self._format_device_data(device) for device in devices]

    def get_devices_by_device_type(self, device_type):
        """Retrieve devices by device type from NetBox"""
        devices = self.conn.dcim.devices.filter(device_type=device_type)
        return [self._format_device_data(device) for device in devices]


class ZabbixClient:
    def __init__(self, url, api_token):
        self.conn = ZabbixAPI(url)
        self.conn.login(token=api_token)

    def host_exists(self, hostname):
        """Check if a host exists in Zabbix"""
        return bool(self.conn.host.get(filter={"host": hostname}))

    def create_host(
        self,
        host_data,
        group_name,
        template_id=None,
        snmp_community="your-snmp-community",
        monitoring_type=None,
    ):
        """Create a host in Zabbix"""
        hostgroup = self._get_or_create_hostgroup(group_name)
        interfaces = self._create_interface(
            host_data["primary_ip"], snmp_community, monitoring_type
        )
        host = {
            "host": host_data["name"],
            "interfaces": interfaces,
            "groups": [{"groupid": hostgroup["groupid"]}],
            "description": host_data["description"],
            "templates": [{"templateid": str(template_id)}] if template_id else [],
        }
        return self.conn.host.create(host)

    def update_host(self, host_id, host_data):
        """Update an existing host in Zabbix"""
        host = {
            "hostid": host_id,
            "host": host_data["name"],
            "description": host_data["description"],
        }
        return self.conn.host.update(host)

    def delete_host(self, host_id):
        """Delete a host from Zabbix"""
        return self.conn.host.delete(host_id)

    def _get_or_create_hostgroup(self, group_name):
        """Retrieve or create a host group in Zabbix"""
        hostgroup = self.conn.hostgroup.get(filter={"name": group_name})
        if not hostgroup:
            hostgroup = self.conn.hostgroup.create(name=group_name)
        # return hostgroup[0]
        if type(hostgroup) is list:
            return hostgroup[0]
        else:
            return hostgroup

    def _create_interface(self, ip, snmp_community, monitoring_type):
        """Create interface configuration based on monitoring type"""
        if not ip:
            return []

        monitoring_type_str = ""
        if monitoring_type:
            if isinstance(monitoring_type, list):
                monitoring_type_str = " ".join(str(x) for x in monitoring_type)
            else:
                monitoring_type_str = str(monitoring_type)

            mt_lower = monitoring_type_str.lower()

            if "snmp" in mt_lower:
                # Determine SNMP version
                if "v1" in mt_lower:
                    return self._create_snmp_interface(ip, snmp_community, version=1)
                elif "v2" in mt_lower:
                    return self._create_snmp_interface(ip, snmp_community, version=2)
                elif "v3" in mt_lower:
                    return self._create_snmp_interface(ip, snmp_community, version=3)
                else:
                    return self._create_snmp_interface(ip, snmp_community, version=2)
            elif "ipmi" in mt_lower:
                return self._create_ipmi_interface(ip)
            elif "jmx" in mt_lower:
                return self._create_jmx_interface(ip)
            elif "agent" in mt_lower:
                return self._create_agent_interface(ip)
            else:
                # Default to SNMP interface if monitoring_type is unknown
                return self._create_snmp_interface(ip, snmp_community, version=2)
        else:
            # Default to SNMP interface if monitoring_type is None
            return self._create_snmp_interface(ip, snmp_community, version=2)

    def _create_snmp_interface(self, ip, snmp_community, version=2):
        """Create SNMP interface configuration"""
        return [
            {
                "type": 2,  # SNMP interface
                "main": 1,
                "useip": 1,
                "ip": ip,
                "dns": "",
                "port": "161",
                "details": {
                    "version": version,
                    "bulk": 1,
                    "community": snmp_community,
                },
            }
        ]

    def _create_ipmi_interface(self, ip):
        """Create IPMI interface configuration"""
        return [
            {
                "type": 3,  # IPMI interface
                "main": 1,
                "useip": 1,
                "ip": ip,
                "dns": "",
                "port": "623",
                "details": {
                    "username": "{$IPMI_USERNAME}",
                    "password": "{$IPMI_PASSWORD}",
                    "auth_protocol": "SHA",
                    "priv_protocol": "AES",
                },
            }
        ]

    def _create_jmx_interface(self, ip):
        """Create JMX interface configuration"""
        return [
            {
                "type": 4,  # JMX interface
                "main": 1,
                "useip": 1,
                "ip": ip,
                "dns": "",
                "port": "1099",
                "details": {
                    "auth_type": 0,
                    "username": "{$JMX_USERNAME}",
                    "password": "{$JMX_PASSWORD}",
                },
            }
        ]

    def _create_agent_interface(self, ip):
        """Create Zabbix agent interface configuration"""
        return [
            {
                "type": 1,  # Zabbix agent interface
                "main": 1,
                "useip": 1,
                "ip": ip,
                "dns": "",
                "port": "10050",
            }
        ]

    def assign_tags_to_host(self, host_id, tags):
        """Assign tags to a host in Zabbix"""
        host = {
            "hostid": host_id,
            "tags": tags,
        }
        return self.conn.host.update(host)

    def assign_template_to_host(self, host_id, template_id):
        """Assign a template to a host in Zabbix"""
        host = {
            "hostid": host_id,
            "templates": [{"templateid": str(template_id)}],
        }
        return self.conn.host.update(host)

    def get_template_id_by_name(self, template_name):
        """Get template ID by name"""
        templates = self.conn.template.get(filter={"host": template_name})
        if templates:
            return templates[0]["templateid"]
        return None

    def update_host_inventory_field(self, host_id, field_name, field_value):
        """Update inventory field for a host in Zabbix"""
        inventory = {
            "hostid": host_id,
            "inventory": {
                field_name: field_value,
            },
        }
        return self.conn.host.update(inventory)

    def set_inventory_mode(self, host_id, mode=1):
        """Enable or disable automatic inventory for a host in Zabbix"""
        return self.conn.host.update(
            {
                "hostid": host_id,
                "inventory_mode": mode,  # 0 - manual, 1 - automatic
            }
        )


class NetboxZabbixSync:
    def __init__(self, config):
        self.config = config
        self.netbox_client = NetBoxClient(config["netbox_url"], config["netbox_token"])
        self.zabbix_client = ZabbixClient(config["zabbix_url"], config["zabbix_token"])

    def sync_device(self, device_name):
        """Sync a single device from NetBox to Zabbix."""
        netbox_device = self.netbox_client.get_device_by_name(device_name)
        if not netbox_device:
            print(f"Device {device_name} not found in NetBox.")
            return

        if not self.zabbix_client.host_exists(netbox_device["name"]):
            self._create_zabbix_host(netbox_device)
            self._update_zabbix_host(netbox_device)
        else:
            self._update_zabbix_host(netbox_device)

    def sync_devices_by_platform(self, platform):
        """Sync all devices from NetBox to Zabbix filtered by platform."""
        devices = self.netbox_client.get_devices_by_platform(platform)
        for device in devices:
            self.sync_device(device["name"])

    def sync_devices_by_device_type(self, device_type):
        """Sync all devices from NetBox to Zabbix filtered by device type."""
        devices = self.netbox_client.get_devices_by_device_type(device_type)
        for device in devices:
            self.sync_device(device["name"])

    def delete_devices_by_platform(self, platform):
        """Delete all devices from Zabbix filtered by platform."""
        devices = self.netbox_client.get_devices_by_platform(platform)
        for device in devices:
            netbox_device = self.netbox_client.get_device_by_name(device["name"])
            if netbox_device:
                zabbix_host = self.zabbix_client.conn.host.get(
                    filter={"host": netbox_device["name"]}
                )
                if zabbix_host:
                    self.zabbix_client.delete_host(zabbix_host[0]["hostid"])
                    print(f"Deleted host: {netbox_device['name']} from Zabbix")
                else:
                    print(f"Host {netbox_device['name']} not found in Zabbix")
            else:
                print(f"Device {device['name']} not found in NetBox")

    def delete_device(self, device_name):
        """Delete a single device from Zabbix."""
        netbox_device = self.netbox_client.get_device_by_name(device_name)
        if not netbox_device:
            print(f"Device {device_name} not found in NetBox.")
            return

        zabbix_host = self.zabbix_client.conn.host.get(
            filter={"host": netbox_device["name"]}
        )
        if zabbix_host:
            self.zabbix_client.delete_host(zabbix_host[0]["hostid"])
            print(f"Deleted host: {netbox_device['name']} from Zabbix")
        else:
            print(f"Host {netbox_device['name']} not found in Zabbix")

    def sync_all_devices(self):
        """Sync all devices from NetBox to Zabbix."""
        devices = self.netbox_client.get_devices()
        for device in devices:
            self.sync_device(device["name"])

    def _create_zabbix_host(self, netbox_device):
        """Create a new host in Zabbix."""
        if netbox_device["primary_ip"]:
            # Get device type object
            device_type = self.netbox_client.conn.dcim.device_types.get(
                model=netbox_device["model"]
            )
            monitoring_type = None
            if device_type:
                monitoring_type = self.netbox_client.get_device_zabbix_monitoring_type(
                    device_type
                )
            self.zabbix_client.create_host(
                netbox_device,
                group_name=self.config["zabbix_group"],
                template_id=self.config["zabbix_template_id"],
                snmp_community=netbox_device.get(
                    "snmp_community", "your-snmp-community"
                ),
                monitoring_type=monitoring_type,  # Pass monitoring type
            )
            print(
                f"Created host: {netbox_device['name']} with IP {netbox_device['primary_ip']} and monitoring type {monitoring_type}"
            )
        else:
            print(f"Skipping {netbox_device['name']} - no primary IP")

    def _update_zabbix_host(self, netbox_device):
        """Update an existing host in Zabbix."""
        existing_host = self.zabbix_client.conn.host.get(
            filter={"host": netbox_device["name"]}
        )[0]
        if existing_host:
            host_id = existing_host["hostid"]
            self.zabbix_client.update_host(host_id, netbox_device)
            print(f"Updated host: {netbox_device['name']} with new attributes")
            self._assign_templates_to_host(netbox_device, host_id)
            self._assign_tags_to_host(netbox_device, host_id)
            # Set automatic inventory
            self.zabbix_client.set_inventory_mode(host_id, mode=1)
            # Assign latitude and longitude to inventory fields
            self.zabbix_client.update_host_inventory_field(
                host_id, "location_lat", netbox_device["latitude"]
            )
            self.zabbix_client.update_host_inventory_field(
                host_id, "location_lon", netbox_device["longitude"]
            )
            self.zabbix_client.update_host_inventory_field(
                host_id, "type", netbox_device["role"]
            )
            self.zabbix_client.update_host_inventory_field(
                host_id, "vendor", netbox_device["manufacturer"]
            )
            self.zabbix_client.update_host_inventory_field(
                host_id, "deployment_status", netbox_device["status"]
            )
            self.zabbix_client.update_host_inventory_field(
                host_id, "oob_ip", netbox_device["primary_ip"]
            )

    def _assign_templates_to_host(self, netbox_device, host_id):
        """Assign Zabbix templates to the host."""
        device_type = self.netbox_client.conn.dcim.device_types.get(
            model=netbox_device["model"]
        )
        if device_type:
            template_names = self.netbox_client.get_device_zabbix_template_name(
                device_type, "ZabbixTemplates"
            )
            if template_names:
                # Ensure template_names is a list
                if not isinstance(template_names, list):
                    template_names = [template_names]
                template_ids = []
                for name in template_names:
                    tid = self.zabbix_client.get_template_id_by_name(name)
                    if tid:
                        template_ids.append({"templateid": str(tid)})
                    else:
                        print(f"Template {name} not found in Zabbix")
                if template_ids:
                    self.zabbix_client.conn.host.update(
                        {"hostid": host_id, "templates": template_ids}
                    )
                    print(
                        f"Assigned template {template_names} to host: {netbox_device['name']}"
                    )
                else:
                    print(
                        f"No valid Zabbix templates found for device type {netbox_device['model']}"
                    )
            else:
                print(
                    f"No Zabbix template found for device type {netbox_device['model']}"
                )
        else:
            print(f"Device type {netbox_device['model']} not found in NetBox")

    def _assign_tags_to_host(self, netbox_device, host_id):
        """Assign tags to the host in Zabbix."""
        tags = [
            {"tag": "site", "value": str(netbox_device["site"] or "")},
            {"tag": "location", "value": str(netbox_device["location"] or "")},
            {"tag": "vendor", "value": str(netbox_device["manufacturer"] or "")},
            {"tag": "model", "value": str(netbox_device["model"] or "")},
            {"tag": "platform", "value": str(netbox_device["platform"] or "")},
            {"tag": "role", "value": str(netbox_device["role"] or "")},
            {"tag": "status", "value": str(netbox_device["status"] or "")},
        ]
        self.zabbix_client.assign_tags_to_host(host_id, tags)
        print(f"Assigned tags to host: {netbox_device['name']}")


if __name__ == "__main__":
    # config = {
    #     # Lab
    #     "netbox_url": "http://192.168.31.114:8000",
    #     "netbox_token": "my-netbox-api-token",
    #     "zabbix_url": "http://192.168.31.112",
    #     "zabbix_token": "my-zabbix-api-token",
    #     "zabbix_group": "Network Devices",
    #     "zabbix_template_id": "10563", # Generic by SNMP
    # }

    # Define configuration
    config = {
        # Prod
        "netbox_url": "https://netbox.example.com",
        "netbox_token": "my-netbox-api-token",
        "zabbix_url": "https://10.1.1.1",
        "zabbix_token": "my-zabbix-api-token",
        # NXG
        # "netbox_url": "https://172.22.2.1",
        # "netbox_token": "my-netbox-api-token",
        # "zabbix_url": "http://172.22.2.2/zabbix",
        # "zabbix_token": "my-zabbix-api-token",
        "zabbix_group": "Network Devices",
        "zabbix_template_id": "10563",  # Generic by SNMP
        # "zabbix_template_id": "10218",  # Cisco IOS by SNMP
    }

    sync = NetboxZabbixSync(config)
    # sync.sync_all_devices()
    # sync.sync_devices_by_platform("ubiquiti_airos")
    # sync.sync_devices_by_platform("tachyon_os")

    # sync.delete_devices_by_platform("cisco_xr")
    # sync.delete_devices_by_platform("mikrotik_routeros")
    # sync.delete_devices_by_platform("merawex_os")
