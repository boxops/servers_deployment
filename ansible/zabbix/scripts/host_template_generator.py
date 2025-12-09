import uuid
import yaml
import csv
from collections import defaultdict
from typing import Dict, List, Optional


class SNMPDataTypeMapper:
    """Maps SNMP data types to Zabbix data types."""

    DATATYPES = {
        "STRING": "CHAR",
        "OID": "CHAR",
        "TIMETICKS": "",
        "BITS": "TEXT",
        "COUNTER": "",
        "COUNTER32": "",
        "COUNTER64": "",
        "GAUGE": "",
        "GAUGE32": "",
        "INTEGER": "FLOAT",
        "INTEGER32": "FLOAT",
        "IPADDR": "TEXT",
        "IPADDRESS": "TEXT",
        "NETADDDR": "TEXT",
        "NOTIF": "",  # SNMP Trap
        "TRAP": "",  # SNMP Trap
        "OBJECTID": "TEXT",
        "OCTETSTR": "TEXT",
        "OCTETSTRING": "TEXT",
        "OPAQUE": "TEXT",
        "TICKS": "",
        "UNSIGNED32": "",
        "WRONG TYPE (SHOULD BE GAUGE32 OR UNSIGNED32)": "TEXT",
        '""': "TEXT",
        "HEX-STRING": "TEXT",
    }

    @classmethod
    def get_data_type(cls, value: str) -> str:
        """Determine the Zabbix data type from SNMP value."""
        snmp_type = (
            value.split(":")[0].strip().upper()
            if ":" in value
            else value.strip().upper()
        )

        if snmp_type not in cls.DATATYPES:
            print(f"Unknown SNMP value type: {snmp_type}. Defaulting to TEXT.")
            return "TEXT"

        if snmp_type in ("NOTIF", "TRAP"):
            print("TODO: Handle SNMP Trap types")
            return ""

        return cls.DATATYPES[snmp_type] or "TEXT"


class ZabbixTemplateGenerator:
    """Generates Zabbix templates from SNMP data."""

    COMMON_TABLE_NAMES = {
        "1.3.6.1.2.1.2.2.1": "Interface Table",
        "1.3.6.1.2.1.4.20.1": "IP Address Table",
        "1.3.6.1.2.1.4.21.1": "IP Route Table",
        "1.3.6.1.2.1.3.1.1": "ARP Table",
        "1.3.6.1.2.1.25.2.3.1": "Storage Table",
        "1.3.6.1.2.1.25.4.2.1": "Process Table",
        "1.3.6.1.4.1.41112.1.3.1.1": "airFiberConfig",
        "1.3.6.1.4.1.41112.1.3.2.1": "airFiberStatus",
        "1.3.6.1.4.1.41112.1.3.3.1": "airFiberStatistics",
        "1.3.6.1.4.1.10002.1.1.1.4.2.1": "airFiberConfig",
        "1.3.6.1.4.1.41112.1.11.1.1": "af60Config",
        "1.3.6.1.4.1.41112.1.11.1.2": "af60Status",
        "1.3.6.1.4.1.41112.1.11.1.3": "af60Station",
        "1.3.6.1.4.1.41112.1.11.1.4": "af60Gps",
        "1.3.6.1.4.1.41112.1.11.1.5": "af60Orientation",
    }

    def __init__(
        self, template_name: str = "SNMP OID Template", template_group: str = "Custom"
    ):
        self.template_name = template_name
        self.template_group = template_group

    @staticmethod
    def generate_uuid() -> str:
        """Generate a UUID without dashes."""
        return str(uuid.uuid4()).replace("-", "")

    def create_template_structure(self) -> Dict:
        """Create basic Zabbix template structure."""
        return {
            "zabbix_export": {
                "version": "7.2",
                "template_groups": [
                    {
                        "uuid": self.generate_uuid(),
                        "name": self.template_group,
                    }
                ],
                "templates": [
                    {
                        "uuid": self.generate_uuid(),
                        "template": self.template_name,
                        "name": self.template_name,
                        "description": "Template created with Zabbix Template Generator from SNMP walk data using iReasoning MIB browser",
                        "groups": [{"name": self.template_group}],
                        "items": [],
                        "discovery_rules": [],
                    }
                ],
            }
        }

    def create_singular_item(self, oid: str, mib_data: Dict) -> Dict:
        """Create a Zabbix item for a singular OID."""
        name = mib_data.get("name", oid)
        return {
            "uuid": self.generate_uuid(),
            "name": name,
            "key": name,
            "type": "SNMP_AGENT",
            "snmp_oid": oid,
            "value_type": SNMPDataTypeMapper.get_data_type(
                mib_data.get("type", "Unknown")
            ),
            "delay": "10m",
            "history": "7d",
            "trends": "0",
            "tags": [
                {"tag": "source", "value": name},
                {"tag": "metric_type", "value": "item"},
            ],
            "preprocessing": [
                {
                    "type": "DISCARD_UNCHANGED_HEARTBEAT",
                    "parameters": ["1h"],
                }
            ],
        }

    def _find_common_prefix(self, names: List[str]) -> Optional[str]:
        """Find the longest common prefix among a list of names."""
        if not names:
            return None

        prefix = names[0]
        for name in names[1:]:
            i = 0
            min_len = min(len(prefix), len(name))
            while i < min_len and prefix[i] == name[i]:
                i += 1
            prefix = prefix[:i]
            if not prefix:
                break

        # Clean up trailing non-letter characters
        while prefix and not prefix[-1].isalpha():
            prefix = prefix[:-1]

        return prefix or None

    def _get_discovery_column(self, columns: Dict) -> tuple:
        """Find the best column to use for discovery (prefer string columns)."""
        for column_id, instances in columns.items():
            for instance in instances:
                if instance["data"]["type"].upper() in {
                    "OCTETSTRING",
                    "STRING",
                    "DISPLAYSTRING",
                }:
                    return column_id, instances
        return next(iter(columns.items()))

    def create_discovery_rule(self, base_oid: str, table_data: Dict) -> Dict:
        """Create a discovery rule for tabular data."""
        column_id, discovery_column = self._get_discovery_column(table_data["columns"])
        discovery_oid = f"{base_oid}.1"

        # Get all names from the table data
        all_names = []
        for instances in table_data["columns"].values():
            for inst in instances:
                if "." in inst["data"]["name"]:
                    base_name = ".".join(inst["data"]["name"].split(".")[:-1])
                    all_names.append(base_name)

        common_prefix = self._find_common_prefix(all_names) or table_data["table_name"]

        discovery_rule = {
            "uuid": self.generate_uuid(),
            "name": common_prefix,
            "type": "SNMP_AGENT",
            "snmp_oid": f"discovery[{{#SNMPVALUE}},{discovery_oid}]",
            "key": f"{common_prefix}.discovery",
            "delay": "12h",
            "item_prototypes": [],
            "preprocessing": [
                {
                    "type": "DISCARD_UNCHANGED_HEARTBEAT",
                    "parameters": ["1h"],
                }
            ],
        }

        for column_id, instances in table_data["columns"].items():
            if not instances:
                continue

            sample = instances[0]["data"]
            name = (
                sample["name"].split(".")[0]
                if "." in sample["name"]
                else sample["name"]
            )

            discovery_rule["item_prototypes"].append(
                {
                    "uuid": self.generate_uuid(),
                    "name": f"{name} {{#SNMPVALUE}}",
                    "type": "SNMP_AGENT",
                    "snmp_oid": f"{base_oid}.{column_id}.{{#SNMPINDEX}}",
                    "key": f"{name}[{{#SNMPVALUE}}]",
                    "value_type": SNMPDataTypeMapper.get_data_type(sample["type"]),
                    "delay": "10m",
                    "history": "7d",
                    "trends": "0",
                    "tags": [{"tag": "source", "value": common_prefix}],
                    "preprocessing": [
                        {
                            "type": "DISCARD_UNCHANGED_HEARTBEAT",
                            "parameters": ["1h"],
                        }
                    ],
                }
            )

        return discovery_rule

    @staticmethod
    def save_template(
        template: Dict, filename: str = "generated_zabbix_template.yaml"
    ) -> None:
        """Save template to YAML file."""
        with open(filename, "w") as f:
            yaml.dump(template, f, sort_keys=False, width=1000)
        print(f"Template saved to {filename}")

    def classify_oids(self, mib_data: Dict) -> Dict:
        """Classify OIDs into singular and tabular."""
        singular = {}
        tabular = defaultdict(lambda: {"table_name": "", "columns": defaultdict(list)})

        for oid, data in mib_data.items():
            # Ensure OID starts with numeric format
            clean_oid = "1." + oid.lstrip(".") if not oid.startswith("1.") else oid
            parts = clean_oid.split(".")

            # Check for singular OIDs (ends with .0 or has no instance part)
            if parts[-1] == "0" or len(parts) <= 2:
                singular[clean_oid] = data
                continue

            # For tabular data, we expect at least 3 parts: base_oid.column.instance
            if len(parts) >= 3:
                base_oid = ".".join(parts[:-2])
                column_id = parts[-2]
                instance_id = parts[-1]

                # Store table information
                if not tabular[base_oid]["table_name"]:
                    tabular[base_oid]["table_name"] = self.COMMON_TABLE_NAMES.get(
                        base_oid, f"Table {base_oid.replace('.', '_')}"
                    )

                tabular[base_oid]["columns"][column_id].append(
                    {"instance_id": instance_id, "full_oid": clean_oid, "data": data}
                )
            else:
                singular[clean_oid] = data

        return {"singular": singular, "tabular": dict(tabular)}

    def _parse_csv(self, filename: str) -> Dict:
        """Parse MIB walk CSV file."""
        mib_data = {}

        with open(filename, "r") as f:
            sample = f.read(1024)
            f.seek(0)
            delimiter = "," if "," in sample else "\t"

            # Read the first line to clean up column names
            first_line = f.readline()
            f.seek(0)

            # Clean up the fieldnames by stripping whitespace
            reader = csv.DictReader(f, delimiter=delimiter)
            if reader.fieldnames:
                reader.fieldnames = [
                    name.strip() if name else None for name in reader.fieldnames
                ]

            for row in reader:
                # print(row)  # Debugging line to see the row content

                # Filter out None keys and handle potential None values
                clean_row = {}
                for k, v in row.items():
                    if k is not None:  # Skip None keys
                        clean_key = k.lower().strip()
                        clean_value = v.strip() if v is not None else ""
                        clean_row[clean_key] = clean_value

                fields = clean_row
                oid = fields.get("oid", fields.get("object_id", "")).strip().lstrip(".")

                if not oid:
                    continue

                mib_data[oid] = {
                    "name": fields.get("name", fields.get("mib_name", oid)),
                    "type": fields.get("type", fields.get("data_type", "Unknown")),
                    "value": fields.get("value", fields.get("data_value", "")),
                }

        return mib_data

    def generate_template_from_csv(self, csv_filename: str) -> Dict:
        """Generate template from CSV file."""
        mib_data = self._parse_csv(csv_filename)
        classified = self.classify_oids(mib_data)
        template = self.create_template_structure()

        # Add singular items
        for oid, data in classified["singular"].items():
            template["zabbix_export"]["templates"][0]["items"].append(
                self.create_singular_item(oid, data)
            )

        # Add discovery rules for tabular data
        for base_oid, table_data in classified["tabular"].items():
            template["zabbix_export"]["templates"][0]["discovery_rules"].append(
                self.create_discovery_rule(base_oid, table_data)
            )

        return template


class ZabbixTemplateBuilder:
    """Orchestrates the template generation process."""

    def __init__(self, template_name: str = "SNMP OID Template"):
        self.generator = ZabbixTemplateGenerator(template_name)

    def build_from_csv(
        self, csv_file: str, output_file: str = "generated_zabbix_template.yaml"
    ) -> Dict:
        """Build template from CSV and save to file."""
        template = self.generator.generate_template_from_csv(csv_file)
        self.generator.save_template(template, output_file)
        return template


def main():
    """Example usage."""
    builder = ZabbixTemplateBuilder("Network Device Template")
    print("Building template from CSV file...")
    template = builder.build_from_csv("mibwalk.csv")
    print("Template generated successfully!")
    return template


if __name__ == "__main__":
    main()
