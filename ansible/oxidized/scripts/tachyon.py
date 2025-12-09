#!/usr/bin/env python3
import requests
import sys
import json
import pprint
from requests.exceptions import RequestException

# Ignore SSL warnings
requests.packages.urllib3.disable_warnings(
    requests.packages.urllib3.exceptions.InsecureRequestWarning
)


class TachyonDevice:
    def __init__(self, ip, username, password, verbose=False):
        self.base_url = f"https://{ip}/cgi.lua/apiv1"
        self.username = username
        self.password = password
        self.verbose = verbose
        self.session = requests.Session()
        self.token = None

    def _debug(self, msg):
        if self.verbose:
            print(f"[DEBUG] {msg}")

    def _handle_response(self, response):
        """Handle and validate JSON responses safely."""
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise Exception(f"Invalid JSON response: {response.text}")
        if "error" in data:
            raise Exception(
                f"API Error: {data['error'].get('details', 'Unknown error')}"
            )
        return data

    def login(self):
        """Authenticate and store session token."""
        url = f"{self.base_url}/login"
        payload = {"username": self.username, "password": self.password}
        try:
            self._debug(f"Logging in to {url} with user '{self.username}'")
            response = self.session.post(url, json=payload, timeout=5, verify=False)
            data = self._handle_response(response)
            self.token = data["token"]
            self.session.headers.update({"Cookie": f"api_token={self.token}"})
            self._debug(f"Login successful. Token: {self.token}")
        except RequestException as e:
            raise Exception(f"Login failed: {e}")

    def logout(self):
        """Log out and clear session token."""
        if not self.token:
            return
        url = f"{self.base_url}/login"
        try:
            self._debug("Logging out...")
            self.session.delete(url, timeout=5, verify=False)
        except RequestException as e:
            self._debug(f"Logout request failed: {e}")
        self.token = None
        self.session.headers.pop("Cookie", None)

    def fetch_config(self):
        """Fetch the current device configuration."""
        url = f"{self.base_url}/config"
        self._debug(f"Fetching config from {url}")
        try:
            response = self.session.get(url, timeout=5, verify=False)
            return self._handle_response(response)
        except RequestException as e:
            raise Exception(f"Failed to fetch config: {e}")

    def push_config(self, config, dry_run=False):
        """Push a new configuration to the device."""
        url = f"{self.base_url}/config"
        payload = {"config": config, "dry_run": dry_run}
        self._debug(f"Pushing config. Dry run: {dry_run}")
        try:
            response = self.session.post(url, json=payload, timeout=10, verify=False)
            data = self._handle_response(response)

            print(f"\nConfig change response: {data['status_msg']}")
            resp = data.get("response", {})
            print(f"\tReboot required: {resp.get('reboot_required')}")
            print(f"\tKeys changed: {resp.get('keys_changed')}")
            print(f"\tKeys added: {resp.get('keys_added')}")
            print(f"\tKeys removed: {resp.get('keys_removed')}")
            print(f"\tWarnings: {resp.get('warnings')}")
            return data
        except RequestException as e:
            raise Exception(f"Failed to push config: {e}")

    def get_stats(self):
        """Fetch device stats (system, wireless, network, ethernet)."""
        url = f"{self.base_url}/stats?type=system,wireless,network,ethernet"
        self._debug(f"Fetching stats from {url}")
        try:
            response = self.session.get(url, timeout=5, verify=False)
            return self._handle_response(response)
        except RequestException as e:
            raise Exception(f"Failed to fetch stats: {e}")

    def set_hostname(self, config, hostname):
        """Update the hostname in the config dict."""
        config["system"]["hostname"] = hostname
        return config

    def change_hostname(self, new_hostname, dry_run=False):
        """Fetch, modify, and push new hostname config."""
        self.login()
        try:
            cfg_data = self.fetch_config()
            config = cfg_data.get("config", {})
            config = self.set_hostname(config, new_hostname)
            self.push_config(config, dry_run=dry_run)
        finally:
            self.logout()


def main():
    if len(sys.argv) != 4:
        print("Usage: tachyon_oxidized.py <host> <username> <password>")
        sys.exit(1)

    ip, username, password = sys.argv[1], sys.argv[2], sys.argv[3]
    device = TachyonDevice(ip, username, password, verbose=False)

    try:
        device.login()
        config_data = device.fetch_config()
        config = config_data.get("config", {})

        # Convert JSON config to a readable string format
        config_str = json.dumps(config, indent=4)
        print(config_str)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        device.logout()


if __name__ == "__main__":
    main()


# if __name__ == "__main__":
#     # Device connection details
#     device_ip = "172.22.1.3"
#     username = "admin"
#     password = "your-device-password"
#     hostname = "hostname-123"
#     dry_run = False
#     verbose_debug = True

#     # Initialize device
#     device = TachyonDevice(device_ip, username, password, verbose=verbose_debug)

#     # Login & fetch system stats
#     try:
#         device.login()
#         # stats = device.get_stats()
#         # pprint.pprint(stats)

#         # Example: Change hostname
#         # device.change_hostname(hostname, dry_run=dry_run)

#         # Example: Fetch and save config
#         config = device.fetch_config()
#         with open("backup_config.json", "w") as f:
#             json.dump(config, f, indent=4)
#     except Exception as e:
#         print(f"Error: {e}")
#     finally:
#         device.logout()
