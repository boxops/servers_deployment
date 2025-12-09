"""
Purpose
    1. Get IP ranges and IP reservations from Netbox
    2. Generate subnet4 config for Kea
    3. Replace subnet4 config in Kea
"""

from sys import argv
from pykeadhcp import Kea
from pynetbox import api
from datetime import datetime
from loguru import logger
from ipaddress import IPv4Address, IPv4Network
from math import floor
from json import dump
from time import sleep
from os import environ
from dotenv import load_dotenv
import urllib3
from pprint import pprint
import schedule
import time

# Load environment variables
load_dotenv()

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Netbox:
    def __init__(self, url, token):
        self.nb = api(url, token=token)
        self.nb.http_session.verify = False

    def get_ip_ranges(self):
        """Fetch and return all IP ranges from NetBox."""
        ip_ranges = self.nb.ipam.ip_ranges.all()
        return [dict(ip_range) for ip_range in ip_ranges]

    def get_host_reservations(self):
        """Fetch and return all global host reservations from NetBox."""
        reservations = []
        # example_reservations = [
        #     {
        #         "reservations": [
        #             {"hw-address": "'D4:81:D7:6D:03:00'", "ip-address": "100.96.32.254"},
        #             {"hw-address": "'D4:81:D7:6D:03:01'", "ip-address": "100.96.32.255"},
        #         ],
        #         "subnet": "100.96.0.0/12",
        #     }
        # ]

        all_host_reservations = self.nb.ipam.ip_addresses.filter(
            cf_DHCPIsReservation=True, cf_IsKeaManaged=True
        )

        for ip_address in all_host_reservations:
            prefixes = self.nb.ipam.prefixes.filter(contains=ip_address.address)
            top_prefix = (
                max(prefixes, key=lambda p: IPv4Network(p.prefix).prefixlen)
                if prefixes
                else None
            )
            if not top_prefix:
                continue

            # Find or create the subnet entry
            subnet_entry = next(
                (r for r in reservations if r["subnet"] == top_prefix.prefix), None
            )
            if not subnet_entry:
                subnet_entry = {"subnet": top_prefix.prefix, "reservations": []}
                reservations.append(subnet_entry)

            circuit_id = ip_address.custom_fields.get("DHCPCircuitID")
            hardware_address = ip_address.custom_fields.get("DHCPHardwareAddress")
            ip = ip_address.address.split("/")[0]

            # Build reservation dict
            if circuit_id and not hardware_address:
                reservation_dict = {"circuit-id": f"'{circuit_id}'", "ip-address": ip}
            elif hardware_address and not circuit_id:
                reservation_dict = {
                    "hw-address": f"{hardware_address}",
                    "ip-address": ip,
                }
            elif hardware_address and circuit_id:
                # default to hardware address if both are present
                reservation_dict = {
                    "hw-address": f"{hardware_address}",
                    "ip-address": ip,
                }
            else:
                continue

            subnet_entry["reservations"].append(reservation_dict)

        return reservations


class KeaDHCP:
    def __init__(self, host, port):
        self.server = Kea(host=host, port=port)

    def push_config(self, config):
        """Push the new configuration to the Kea server."""
        # Remove 'hash' if present
        if "hash" in config["arguments"]:
            del config["arguments"]["hash"]

        set_config = self.server.dhcp4.config_set(config["arguments"])
        logger.info(f"Config Set Result: {set_config}")
        assert set_config["result"] == 0

        test_config = self.server.dhcp4.config_test(config["arguments"])
        logger.info(f"Config Test Result: {test_config}")
        assert test_config["result"] == 0

        write_config = self.server.dhcp4.config_write("/etc/kea/kea-dhcp4.conf")
        logger.info(f"Config Write Result: {write_config}")
        assert write_config["result"] == 0

    def replace_subnet4(self, new_subnet4):
        """Replace the 'subnet4' configuration."""
        config = self.server.dhcp4.config_get()
        logger.info(f"Fetched current configuration: {config}")

        # Remove 'hash' if present
        if "hash" in config["arguments"]:
            del config["arguments"]["hash"]

        config["arguments"]["Dhcp4"]["subnet4"] = new_subnet4
        self.push_config(config)

    def replace_shared_networks(self, new_shared_networks):
        """Replace the 'shared-networks' configuration."""
        config = self.server.dhcp4.config_get()
        logger.info(f"Fetched current configuration: {config}")

        # Remove 'hash' if present
        if "hash" in config["arguments"]:
            del config["arguments"]["hash"]

        config["arguments"]["Dhcp4"]["shared-networks"] = new_shared_networks
        self.push_config(config)

    # def replace_subnet4(self, new_subnet):
    #     """Replace the subnet4 configuration on the Kea DHCP server."""
    #     config = self.server.dhcp4.config_get()

    #     if config["arguments"]["Dhcp4"]["subnet4"] != new_subnet:
    #         config["arguments"]["Dhcp4"]["subnet4"] = new_subnet
    #         self.push_config(config)
    #     else:
    #         logger.info("Subnet4 configuration is already up-to-date")

    # def replace_shared_networks(self, shared_networks, reservations):
    #     """Replace the shared networks and reservations on the Kea DHCP server."""
    #     config = self.server.dhcp4.config_get()

    #     if config["arguments"]["Dhcp4"]["shared-networks"] != shared_networks:
    #         config["arguments"]["Dhcp4"]["shared-networks"] = shared_networks
    #         self.push_config(config)
    #     else:
    #         logger.info("Shared-networks configuration is already up-to-date")

    #     # Manage global reservations
    #     if reservations:
    #         for reservation in reservations:
    #             circuit_id = reservation["circuit-id"]
    #             ip_address = reservation["ip-address"]

    #             existing_reservations = config["arguments"]["Dhcp4"].get(
    #                 "reservations", []
    #             )
    #             reservation_exists = any(
    #                 res["ip-address"] == ip_address and res["circuit-id"] == circuit_id
    #                 for res in existing_reservations
    #             )

    #             if not reservation_exists:
    #                 logger.info(
    #                     f"Adding new reservation for IP {ip_address} with circuit ID {circuit_id}"
    #                 )
    #                 existing_reservations.append(reservation)

    #         config["arguments"]["Dhcp4"]["reservations"] = existing_reservations
    #         self.push_config(config)


class SubnetConfig:
    @staticmethod
    def split_pool(start_address, end_address, verbose=False):
        """Split a pool into two equal parts and return them."""
        start = int(IPv4Address(start_address))
        end = int(IPv4Address(end_address))
        total_ips = end - start
        halve_pool = floor(total_ips / 2)

        primary_pool = f"{start_address}-{IPv4Address(start_address) + halve_pool}"
        secondary_pool = f"{IPv4Address(start_address) + halve_pool + 1}-{end_address}"

        split_pools = [primary_pool, secondary_pool]

        if verbose:
            logger.info(f"Split pools: {split_pools}")

        return split_pools

    @staticmethod
    def get_subnets(ip_ranges):
        """Extract and return subnets from IP ranges in NetBox."""
        new_subnets = []
        subnets_only = []

        for ip_range in ip_ranges:
            subnet = ip_range.get("custom_fields").get("DHCPPoolSubnet")
            if subnet and subnet not in subnets_only:
                subnets_only.append(subnet)
                new_subnets.append({"subnet": subnet})

        return new_subnets, subnets_only

    @staticmethod
    def attach_pools(ip_ranges, new_subnets, verbose=False):
        """Attach pools to the correct subnets if DHCPCreatePools is True."""
        for ip_range in ip_ranges:
            create_pools = ip_range.get("custom_fields", {}).get(
                "DHCPCreatePools", True
            )
            if not create_pools:
                continue
            start_address = ip_range.get("start_address").split("/")[0]
            end_address = ip_range.get("end_address").split("/")[0]

            for new_subnet in new_subnets:
                if new_subnet["subnet"] == ip_range.get("custom_fields").get(
                    "DHCPPoolSubnet"
                ):
                    if "pools" not in new_subnet:
                        new_subnet["pools"] = []
                    new_subnet["pools"].append(
                        {"pool": f"{start_address}-{end_address}"}
                    )
        return new_subnets

    @staticmethod
    def attach_default_gateway(ip_ranges, new_subnets):
        """Attach default gateways to the correct subnets."""
        for ip_range in ip_ranges:
            for new_subnet in new_subnets:
                if new_subnet["subnet"] == ip_range.get("custom_fields").get(
                    "DHCPPoolSubnet"
                ):
                    gateway = ip_range.get("custom_fields").get(
                        "DHCPPoolDefaultGateway"
                    )
                    if gateway:
                        if "option-data" not in new_subnet:
                            new_subnet["option-data"] = []

                        new_subnet["option-data"].append(
                            {"name": "routers", "data": gateway}
                        )

        return new_subnets

    @staticmethod
    def attach_relay_ip(ip_ranges, new_subnets):
        """Attach relay IPs to the correct subnets."""
        for ip_range in ip_ranges:
            for new_subnet in new_subnets:
                if new_subnet["subnet"] == ip_range.get("custom_fields").get(
                    "DHCPPoolSubnet"
                ):
                    relay_ips = ip_range.get("custom_fields").get("DHCPPoolRelayIPs")
                    if relay_ips:
                        if "relay" not in new_subnet:
                            new_subnet["relay"] = {"ip-addresses": []}

                        new_subnet["relay"]["ip-addresses"].extend(relay_ips.split(","))

        return new_subnets

    @staticmethod
    def attach_option_data(ip_ranges, new_subnets):
        """Attach option data to the correct subnets."""
        for ip_range in ip_ranges:
            for new_subnet in new_subnets:
                if new_subnet["subnet"] == ip_range.get("custom_fields").get(
                    "DHCPPoolSubnet"
                ):
                    option_data = ip_range.get("custom_fields").get("DHCPPoolOptions")
                    # "DHCPPoolOptions": [
                    #     {
                    #         "data": "192.0.2.3",
                    #         "name": "domain-name-servers"
                    #     }
                    # ],

                    if option_data:
                        if "option-data" not in new_subnet:
                            new_subnet["option-data"] = []

                        new_subnet["option-data"].extend(option_data)

        return new_subnets

    @staticmethod
    def attach_reservations(new_subnets, reservations):
        """Attach reservations to the correct subnets by IP inclusion."""
        # logger.info(f"Reservations argument: {reservations}")
        # Flatten all reservation entries to (ip, dict) pairs
        flat_reservations = []
        for reservation_group in reservations:
            entries = reservation_group.get("reservations", [])
            for entry in entries:
                ip = entry.get("ip-address")
                flat_reservations.append((ip, entry))

        # For each subnet, attach reservations whose IP falls within the subnet
        for new_subnet in new_subnets:
            subnet_cidr = new_subnet["subnet"]
            net = IPv4Network(subnet_cidr)
            for ip, entry in flat_reservations:
                if ip and IPv4Address(ip) in net:
                    if "reservations" not in new_subnet:
                        new_subnet["reservations"] = []
                    new_subnet["reservations"].append(entry)
        #             logger.info(f"Added reservation {entry} to subnet {subnet_cidr}")
        # logger.info(f"Subnets after attaching reservations: {new_subnets}")
        return new_subnets

    @staticmethod
    def generate_subnet4(ip_ranges, reservations, verbose=False):
        """Generate the subnet4 configuration."""
        new_subnets, subnets_only = SubnetConfig.get_subnets(ip_ranges)
        new_subnets = SubnetConfig.attach_pools(ip_ranges, new_subnets, verbose)
        new_subnets = SubnetConfig.attach_default_gateway(ip_ranges, new_subnets)
        new_subnets = SubnetConfig.attach_relay_ip(ip_ranges, new_subnets)
        new_subnets = SubnetConfig.attach_option_data(ip_ranges, new_subnets)
        new_subnets = SubnetConfig.attach_reservations(new_subnets, reservations)

        # Add unique 'id' field to each subnet
        for i, subnet in enumerate(new_subnets):
            subnet["id"] = i + 1

        # logger.info(f"Generated subnets: {new_subnets}")

        with open("subnet4.json", "w") as f:
            dump(new_subnets, f, indent=4)

        return new_subnets

    # @staticmethod
    # def generate_shared_networks(ip_ranges, netbox_api, verbose=False):
    #     """Generate the shared networks configuration."""
    #     new_subnets, subnets_only = SubnetConfig.get_subnets(ip_ranges)
    #     new_subnets = SubnetConfig.attach_pools(ip_ranges, new_subnets, verbose)
    #     new_subnets = SubnetConfig.attach_default_gateway(ip_ranges, new_subnets)
    #     new_subnets = SubnetConfig.attach_relay_ip(ip_ranges, new_subnets)
    #     new_subnets = SubnetConfig.attach_option_data(ip_ranges, new_subnets)

    #     shared_networks = [{"name": "CISCO-IPOE", "subnet4": new_subnets}]

    #     with open("shared_networks.json", "w") as f:
    #         dump(shared_networks, f, indent=4)

    #     return shared_networks


class Manager:
    def __init__(self, netbox_url, netbox_token, kea_host, kea_port):
        self.netbox_api = Netbox(netbox_url, netbox_token)
        self.kea_dhcp = KeaDHCP(kea_host, kea_port)

    def run(self):
        logger.info("Fetching IP ranges from NetBox")
        ip_ranges = self.netbox_api.get_ip_ranges()
        reservations = self.netbox_api.get_host_reservations()

        logger.info("Generating subnet4 configuration")
        new_subnets = SubnetConfig.generate_subnet4(ip_ranges, reservations)

        logger.info("Replacing subnet4 configuration on Kea DHCP server")
        self.kea_dhcp.replace_subnet4(new_subnets)

        # logger.info("Generating shared networks configuration")
        # shared_networks = SubnetConfig.generate_shared_networks(ip_ranges, self.netbox_api)

        # logger.info("Replacing shared networks configuration on Kea DHCP server")
        # self.kea_dhcp.replace_shared_networks(shared_networks, reservations)


def main():
    """
    Main script execution logic.
    """
    logger.add("netbox_dhcp.log", retention="7 days", level="INFO")

    if len(argv) != 2:
        print("Usage: python netbox_kea_replace_subnet4.py <DHCP_SERVER_IP>")
        return

    dhcp_server_ip = argv[1]

    netbox_url = environ.get("NETBOX_URL")
    netbox_token = environ.get("NETBOX_TOKEN")
    kea_port = environ.get("KEA_PORT")

    if not all([netbox_url, netbox_token, dhcp_server_ip, kea_port]):
        logger.error("Missing required environment variables or argument. Exiting.")
        return

    kea_host = f"http://{dhcp_server_ip}"

    manager = Manager(netbox_url, netbox_token, kea_host, kea_port)
    manager.run()

    # # Schedule the script to run periodically, e.g., every 5 minutes
    # schedule.every(5).minutes.do(manager.run)

    # while True:
    #     schedule.run_pending()
    #     time.sleep(1)


if __name__ == "__main__":
    main()
