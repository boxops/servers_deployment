"""
Open the file `zabbix_template.yaml` and replace all UUIDs with new ones.
"""

import uuid
import yaml
from pathlib import Path
import re


def generate_uuid() -> str:
    """Generate a UUID without dashes."""
    return str(uuid.uuid4()).replace("-", "")


def replace_uuids(file_path):
    with open(file_path, "r") as file:
        content = file.read()

    # Load the YAML content
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise ValueError("YAML content is not a valid dictionary.")

    # Find all UUIDs in the content with key "uuid"
    # Example UUID: aedaca312e2f4732b1d086bfbbebdc16
    uuid_pattern = re.compile(r"\b[a-f0-9]{32}\b")
    uuids_found = uuid_pattern.findall(content)
    if not uuids_found:
        print("No UUIDs found in the file.")
        return

    # Replace each UUID with a new one
    for old_uuid in uuids_found:
        new_uuid = generate_uuid()
        content = content.replace(old_uuid, new_uuid)
        # print(f"Replaced UUID {old_uuid} with {new_uuid}")

    # Write the modified content back to the file
    with open(file_path, "w") as file:
        file.write(content)


if __name__ == "__main__":
    # Specify the path to the YAML file
    file_path = Path("generated_zabbix_template.yaml")

    if not file_path.exists():
        print(f"File {file_path} does not exist.")
    else:
        replace_uuids(file_path)
        print(f"UUIDs in {file_path} have been replaced.")
