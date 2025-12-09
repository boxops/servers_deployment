import subprocess


class SNMPWalker:
    """
    Class to handle SNMP walk operations and output parsing.
    """

    def __init__(self, host, community, version="2c"):
        """
        Initialize the SNMP walker.

        :param host: The IP address or hostname of the SNMP device.
        :param community: The SNMP community string.
        :param version: The SNMP version (default is "2c").
        """
        self.host = host
        self.community = community
        self.version = version

    def run_snmpwalk(self, oid):
        """
        Run the snmpwalk command to retrieve OID tree from the device.

        :param oid: The OID to start the walk from.
        :return: The output of the snmpwalk command.
        """
        command = [
            "snmpwalk",
            f"-v{self.version}",
            "-c",
            self.community,
            self.host,
            oid,
        ]
        result = subprocess.run(command, capture_output=True, text=True)

        if result.returncode != 0:
            raise RuntimeError(f"snmpwalk failed: {result.stderr.strip()}")

        return result.stdout.strip()

    def save_snmpwalk_output(self, output, filename="snmpwalk_output.txt"):
        """
        Save the output of the snmpwalk command to a file.

        :param output: The output from the snmpwalk command.
        :param filename: The name of the file to save the output to.
        """
        with open(filename, "w") as file:
            file.write(output)
        print(f"SNMP walk output saved to {filename}")

    @staticmethod
    def parse_snmpwalk_output(output):
        """
        Parse the output of the snmpwalk command into a dictionary.

        :param output: The output from the snmpwalk command.
        :return: A dictionary with OIDs as keys and their values.
        """
        oid_dict = {}
        for line in output.splitlines():
            if " = " in line:
                oid, value = line.split(" = ", 1)
                # replace iso in oid with 1
                oid = oid.replace("iso", "1")
                oid_dict[oid.strip()] = value.strip()
        return oid_dict

    @staticmethod
    def load_snmpwalk_from_file(filename):
        """
        Load SNMP walk output from a file.

        :param filename: The name of the file containing the SNMP walk output.
        :return: The content of the file as a string.
        """
        try:
            with open(filename, "r") as file:
                return file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"File {filename} not found")


if __name__ == "__main__":
    # Example usage
    walker = SNMPWalker(host="192.168.31.47", community="public")
    output = walker.run_snmpwalk("1.3.6.1.2.1")
    walker.save_snmpwalk_output(output, "snmpwalk_output.txt")
