import os
import glob
from typing import List, Dict, Any, Optional
from zabbix_utils import ZabbixAPI
import ssl
import requests


class ZabbixTemplateExporter:
    """
    A class to handle exporting Zabbix templates from a Zabbix server.
    """

    def __init__(self, url: str, token: str, output_dir: str = "zabbix_templates"):
        """
        Initialize the ZabbixTemplateExporter.

        Args:
            url (str): The Zabbix server URL
            token (str): The API token for authentication
            output_dir (str): Directory to save exported templates
        """
        self.url = url
        self.token = token
        self.output_dir = output_dir
        self.api: Optional[ZabbixAPI] = None
        self._configure_ssl()

    def _configure_ssl(self) -> None:
        """Configure SSL settings to disable warnings and verification."""
        requests.packages.urllib3.disable_warnings(
            requests.packages.urllib3.exceptions.InsecureRequestWarning
        )
        ssl._create_default_https_context = ssl._create_unverified_context

    def connect(self) -> None:
        """Establish connection to Zabbix API."""
        self.api = ZabbixAPI(url=self.url)
        self.api.login(token=self.token)

    def disconnect(self) -> None:
        """Disconnect from Zabbix API."""
        if self.api:
            self.api.logout()
            self.api = None

    def get_group_id_by_name(self, group_name: str) -> Optional[str]:
        """
        Get the group ID for a given group name.

        Args:
            group_name (str): Name of the group

        Returns:
            Optional[str]: Group ID if found, else None
        """
        if not self.api:
            raise RuntimeError("Not connected to Zabbix API. Call connect() first.")

        # Get group ID
        # {
        #     "jsonrpc": "2.0",
        #     "method": "templategroup.get",
        #     "params": {"output": "extend", "filter": {"name": ["Custom"]}},
        #     "id": 1,
        # }

        get_group_id = self.api.templategroup.get(
            output=["groupid", "name"], filter={"name": [group_name]}
        )
        groups = self.api.template.get(
            output=["groupid", "name"], filter={"name": [group_name]}
        )
        return groups[0]["groupid"] if groups else None

        # groups = self.api.templategroup.get(output=["groupid", "name"])
        # for group in groups:
        #     if group["name"] == group_name:
        #         return group["groupid"]
        # return None

    def get_templates_filtered_by_group(self, group_name: str) -> List[Dict[str, Any]]:
        # Correct API body:
        # {
        #     "jsonrpc": "2.0",
        #     "method": "templategroup.get",
        #     "params": {
        #         "output": "extend",
        #         "filter": {
        #             "name": [
        #                 "Custom"
        #             ]
        #         }
        #     },
        #     "id": 1
        # }
        get_group_id = self.api.templategroup.get(
            output=["groupid", "name"], filter={"name": [group_name]}
        )
        if not get_group_id:
            return []

        group_id = get_group_id[0]["groupid"]
        return self.api.template.get(output=["templateid", "name"], groupids=group_id)

    def get_all_templates(self) -> List[Dict[str, Any]]:
        """
        Get all templates from the Zabbix server.

        Returns:
            List[Dict[str, Any]]: List of template information
        """
        if not self.api:
            raise RuntimeError("Not connected to Zabbix API. Call connect() first.")

        return self.api.template.get(
            output=["groupid", "name"],
            selectTemplateGroups="extend",
            limit=1000,  # or a higher value, or remove for unlimited if supported
        )

    def filter_templates_by_group(
        self, templates: List[Dict[str, Any]], group_name: str
    ) -> List[Dict[str, Any]]:
        """
        Filter templates by group name.

        Args:
            templates (List[Dict[str, Any]]): List of templates
            group_name (str): Name of the group to filter by

        Returns:
            List[Dict[str, Any]]: Filtered templates
        """
        return [
            template
            for template in templates
            if group_name
            in [group["name"] for group in template.get("templategroups", [])]
        ]

    def export_templates_configuration(
        self, template_ids: List[str], format_type: str = "yaml"
    ) -> str:
        """
        Export configuration for specified template IDs.

        # Existing code continues here...
        Args:
            template_ids (List[str]): List of template IDs to export
            format_type (str): Export format (yaml, xml, json)

        Returns:
            str: Exported configuration
        """
        if not self.api:
            raise RuntimeError("Not connected to Zabbix API. Call connect() first.")

        return self.api.configuration.export(
            options={"templates": template_ids}, format=format_type
        )

    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename by replacing problematic characters.

        Args:
            filename (str): Original filename

        Returns:
            str: Sanitized filename
        """
        return filename.replace("/", "_")

    def save_template_to_file(self, template_name: str, configuration: str) -> str:
        """
        Save template configuration to a file.

        Args:
            template_name (str): Name of the template
            configuration (str): Template configuration content

        Returns:
            str: Path to the saved file
        """
        os.makedirs(self.output_dir, exist_ok=True)
        sanitized_name = self._sanitize_filename(template_name)
        file_path = os.path.join(self.output_dir, f"{sanitized_name}.yaml")

        with open(file_path, mode="w", encoding="utf-8") as f:
            f.write(configuration)

        return file_path

    def export_templates_by_group(self, group_name: str = "Custom") -> None:
        """
        Export all templates from a specific group, each template to its own file.

        Args:
            group_name (str): Name of the group to export templates from
        """
        try:
            templates_in_group = self.get_templates_filtered_by_group(group_name)

            print(
                f"Found {len(templates_in_group)} templates in group '{group_name}'. Exporting each to individual files..."
            )

            # Export each template individually
            for template in templates_in_group:
                template_id = template["templateid"]
                template_name = template["name"]

                # Export configuration for this specific template only
                configuration = self.export_templates_configuration([template_id])

                # Save this template to its own file
                file_path = self.save_template_to_file(template_name, configuration)
                print(f"Exported template '{template_name}' to {file_path}")

        except Exception as e:
            print(f"Error exporting templates: {e}")
            raise

    def export_single_template(
        self, template_name: str = None, template_id: str = None
    ) -> str:
        """
        Export a single template by name or ID.

        Args:
            template_name (str, optional): Name of the template to export
            template_id (str, optional): ID of the template to export

        Returns:
            str: Path to the exported file
        """
        if not template_name and not template_id:
            raise ValueError("Either template_name or template_id must be provided")

        try:
            if template_name and not template_id:
                # Find template by name
                all_templates = self.get_all_templates()
                matching_templates = [
                    t for t in all_templates if t["name"] == template_name
                ]

                if not matching_templates:
                    raise ValueError(f"Template with name '{template_name}' not found")

                template_id = matching_templates[0]["templateid"]
                template_name = matching_templates[0]["name"]

            elif template_id and not template_name:
                # Find template by ID to get the name
                all_templates = self.get_all_templates()
                matching_templates = [
                    t for t in all_templates if t["templateid"] == template_id
                ]

                if not matching_templates:
                    raise ValueError(f"Template with ID '{template_id}' not found")

                template_name = matching_templates[0]["name"]

            # Export configuration for this specific template
            configuration = self.export_templates_configuration([template_id])

            # Save template to file
            file_path = self.save_template_to_file(template_name, configuration)
            print(
                f"Exported template '{template_name}' (ID: {template_id}) to {file_path}"
            )

            return file_path

        except Exception as e:
            print(f"Error exporting single template: {e}")
            raise

    def export_all_templates_to_single_file(
        self, group_name: str = "Custom", filename: str = None
    ) -> str:
        """
        Export all templates from a specific group to a single file.

        Args:
            group_name (str): Name of the group to export templates from
            filename (str, optional): Custom filename for the export file

        Returns:
            str: Path to the exported file
        """
        try:
            # Get all templates
            all_templates = self.get_all_templates()

            # Filter templates by group
            templates_in_group = self.filter_templates_by_group(
                all_templates, group_name
            )

            if not templates_in_group:
                print(f"No templates found in group '{group_name}'")
                return None

            # Get template IDs
            template_ids = [template["templateid"] for template in templates_in_group]

            # Export configuration for all templates in the group
            configuration = self.export_templates_configuration(template_ids)

            # Determine filename
            if not filename:
                filename = f"{group_name}_all_templates"

            # Save all templates to a single file
            file_path = self.save_template_to_file(filename, configuration)
            print(
                f"Exported {len(templates_in_group)} templates from group '{group_name}' to {file_path}"
            )

            return file_path

        except Exception as e:
            print(f"Error exporting templates: {e}")
            raise

    def get_templates_info(self, group_name: str = None) -> Dict[str, Any]:
        """
        Get information about templates, optionally filtered by group.

        Args:
            group_name (str, optional): Group name to filter by

        Returns:
            Dict[str, Any]: Template information
        """
        all_templates = self.get_all_templates()

        if group_name:
            filtered_templates = self.filter_templates_by_group(
                all_templates, group_name
            )
            return {
                "total_templates": len(all_templates),
                "filtered_templates": len(filtered_templates),
                "group_name": group_name,
                "templates": filtered_templates,
            }
        else:
            return {"total_templates": len(all_templates), "templates": all_templates}


def main():
    """Main function to demonstrate usage."""
    # Configuration
    URL = "https://10.1.1.1"
    TOKEN = "my_token_here"

    # Example 1: Export templates
    print("=== TEMPLATE EXPORT EXAMPLE ===")
    exporter = ZabbixTemplateExporter(url=URL, token=TOKEN)

    try:
        exporter.connect()

        # Export templates from 'Custom' group (each template to its own file)
        print("Exporting each template to individual files...")
        exporter.export_templates_by_group("Custom")

    finally:
        exporter.disconnect()

    print("\n" + "=" * 50)


def demo_export_only():
    """Demo function showing only export functionality."""
    URL = "https://10.0.1.1"
    TOKEN = "my_token_here"

    exporter = ZabbixTemplateExporter(url=URL, token=TOKEN)

    try:
        exporter.connect()
        exporter.export_templates_by_group("Custom")
    finally:
        exporter.disconnect()


if __name__ == "__main__":
    main()

    # Uncomment the following line to run the export demo
    # demo_export_only()
