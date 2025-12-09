import os
import glob
from typing import List, Dict, Any, Optional
from zabbix_utils import ZabbixAPI
import ssl
import requests


class ZabbixTemplateImporter:
    """
    A class to handle importing Zabbix templates to a Zabbix server.
    """

    def __init__(self, url: str, token: str, templates_dir: str = "zabbix_templates"):
        """
        Initialize the ZabbixTemplateImporter.

        Args:
            url (str): The Zabbix server URL
            token (str): The API token for authentication
            templates_dir (str): Directory containing template files to import
        """
        self.url = url
        self.token = token
        self.templates_dir = templates_dir
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

    def get_template_files(self, file_pattern: str = "*.yaml") -> List[str]:
        """
        Get list of template files in the templates directory.

        Args:
            file_pattern (str): File pattern to match (default: *.yaml)

        Returns:
            List[str]: List of template file paths
        """
        if not os.path.exists(self.templates_dir):
            raise FileNotFoundError(
                f"Templates directory '{self.templates_dir}' not found"
            )

        pattern = os.path.join(self.templates_dir, file_pattern)
        template_files = glob.glob(pattern)

        if not template_files:
            print(
                f"No template files found in '{self.templates_dir}' matching pattern '{file_pattern}'"
            )

        return template_files

    def read_template_file(self, file_path: str) -> str:
        """
        Read template configuration from file.

        Args:
            file_path (str): Path to the template file

        Returns:
            str: Template configuration content
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Template file '{file_path}' not found")

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    def import_template_configuration(
        self,
        configuration: str,
        create_missing: bool = True,
        update_existing: bool = True,
        delete_missing: bool = True,
    ) -> Dict[str, Any]:
        """
        Import template configuration to Zabbix server.

        Args:
            configuration (str): Template configuration content
            update_existing (bool): Whether to update existing templates
            delete_missing (bool): Whether to delete missing elements

        Returns:
            Dict[str, Any]: Import result from Zabbix API
        """
        if not self.api:
            raise RuntimeError("Not connected to Zabbix API. Call connect() first.")

        import_rules = {
            "templates": {
                "createMissing": create_missing,
                "updateExisting": update_existing,
                # "deleteMissing": delete_missing,
            },
            # "hostGroups": {
            #     "createMissing": True,
            #     "updateExisting": update_existing,
            # },
            "hosts": {
                "createMissing": create_missing,
                "updateExisting": update_existing,
            },
            "items": {
                "createMissing": create_missing,
                "updateExisting": update_existing,
                # "deleteMissing": delete_missing,
            },
            "discoveryRules": {
                "createMissing": create_missing,
                "updateExisting": update_existing,
                # "deleteMissing": delete_missing,
            },
            "triggers": {
                "createMissing": create_missing,
                "updateExisting": update_existing,
                # "deleteMissing": delete_missing,
            },
            "graphs": {
                "createMissing": create_missing,
                "updateExisting": update_existing,
                # "deleteMissing": delete_missing,
            },
            "valueMaps": {
                "createMissing": create_missing,
                "updateExisting": update_existing,
            },
        }

        return self.api.configuration.import_(
            source=configuration, format="yaml", rules=import_rules
        )

    def import_single_template(
        self,
        template_file: str,
        update_existing: bool = True,
        delete_missing: bool = False,
    ) -> Dict[str, Any]:
        """
        Import a single template from file.

        Args:
            template_file (str): Path to template file or just filename (will look in templates_dir)
            update_existing (bool): Whether to update existing templates
            delete_missing (bool): Whether to delete missing elements

        Returns:
            Dict[str, Any]: Import result
        """
        try:
            # If just filename provided, look in templates directory
            if not os.path.dirname(template_file):
                template_file = os.path.join(self.templates_dir, template_file)

            # Read template configuration
            configuration = self.read_template_file(template_file)

            # Import template
            result = self.import_template_configuration(
                configuration, update_existing, delete_missing
            )

            filename = os.path.basename(template_file)
            print(f"Successfully imported template from '{filename}'")

            return result

        except Exception as e:
            print(f"Error importing template from '{template_file}': {e}")
            raise

    def import_all_templates(
        self,
        file_pattern: str = "*.yaml",
        update_existing: bool = True,
        delete_missing: bool = False,
        stop_on_error: bool = False,
    ) -> Dict[str, Any]:
        """
        Import all templates from the templates directory.

        Args:
            file_pattern (str): File pattern to match
            update_existing (bool): Whether to update existing templates
            delete_missing (bool): Whether to delete missing elements
            stop_on_error (bool): Whether to stop on first error

        Returns:
            Dict[str, Any]: Summary of import results
        """
        template_files = self.get_template_files(file_pattern)

        if not template_files:
            return {
                "total_files": 0,
                "successful_imports": 0,
                "failed_imports": 0,
                "results": [],
            }

        print(f"Found {len(template_files)} template files. Starting import...")

        successful_imports = 0
        failed_imports = 0
        results = []

        for template_file in template_files:
            filename = os.path.basename(template_file)
            try:
                result = self.import_single_template(
                    template_file, update_existing, delete_missing
                )
                successful_imports += 1
                results.append(
                    {"file": filename, "status": "success", "result": result}
                )

            except Exception as e:
                failed_imports += 1
                error_msg = str(e)
                results.append(
                    {"file": filename, "status": "failed", "error": error_msg}
                )
                print(f"Failed to import '{filename}': {error_msg}")

                if stop_on_error:
                    print("Stopping import process due to error")
                    break

        summary = {
            "total_files": len(template_files),
            "successful_imports": successful_imports,
            "failed_imports": failed_imports,
            "results": results,
        }

        print(f"\nImport Summary:")
        print(f"Total files processed: {summary['total_files']}")
        print(f"Successful imports: {summary['successful_imports']}")
        print(f"Failed imports: {summary['failed_imports']}")

        return summary

    def list_template_files(self, file_pattern: str = "*.yaml") -> List[Dict[str, str]]:
        """
        List available template files with basic information.

        Args:
            file_pattern (str): File pattern to match

        Returns:
            List[Dict[str, str]]: List of template file information
        """
        template_files = self.get_template_files(file_pattern)
        file_info = []

        for file_path in template_files:
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            modification_time = os.path.getmtime(file_path)

            file_info.append(
                {
                    "filename": filename,
                    "full_path": file_path,
                    "size_bytes": file_size,
                    "modified_timestamp": modification_time,
                }
            )

        return file_info

    def validate_template_file(self, template_file: str) -> Dict[str, Any]:
        """
        Validate a template file without importing it.

        Args:
            template_file (str): Path to template file

        Returns:
            Dict[str, Any]: Validation result
        """
        try:
            # If just filename provided, look in templates directory
            if not os.path.dirname(template_file):
                template_file = os.path.join(self.templates_dir, template_file)

            # Check if file exists
            if not os.path.exists(template_file):
                return {"valid": False, "error": f"File '{template_file}' not found"}

            # Read file content
            configuration = self.read_template_file(template_file)

            # Basic validation - check if it's not empty and has some expected content
            if not configuration.strip():
                return {"valid": False, "error": "File is empty"}

            # Check for basic YAML structure (very basic validation)
            if "zabbix_export:" not in configuration:
                return {
                    "valid": False,
                    "error": "File doesn't appear to be a Zabbix export format",
                }

            return {
                "valid": True,
                "file_size": len(configuration),
                "filename": os.path.basename(template_file),
            }

        except Exception as e:
            return {"valid": False, "error": str(e)}


def main():
    """Main function to demonstrate the ZabbixTemplateImporter functionality."""
    # Example 2: Import templates
    print("=== TEMPLATE IMPORT EXAMPLE ===")
    importer = ZabbixTemplateImporter(url=URL, token=TOKEN)

    try:
        importer.connect()

        # List available template files
        print("\nListing available template files:")
        template_files = importer.list_template_files()
        for file_info in template_files[:5]:  # Show first 5 files
            print(f"  - {file_info['filename']} ({file_info['size_bytes']} bytes)")
        if len(template_files) > 5:
            print(f"  ... and {len(template_files) - 5} more files")

        # Import a single template
        print("\nImporting a single template:")
        importer.import_single_template("Tachyon TNA-303X.yaml")

        # # Import all templates
        # print("\nImporting all templates:")
        # summary = importer.import_all_templates(
        #     update_existing=True, stop_on_error=False
        # )

        # Example: Validate a template file
        if template_files:
            first_file = template_files[0]["filename"]
            print(f"\nValidating template file: {first_file}")
            validation = importer.validate_template_file(first_file)
            if validation["valid"]:
                print(f"  ✓ File is valid ({validation['file_size']} characters)")
            else:
                print(f"  ✗ File is invalid: {validation['error']}")

    finally:
        importer.disconnect()


if __name__ == "__main__":
    # Lab
    URL = "http://192.168.31.112"
    TOKEN = "my-zabbix-api-token"

    main()
