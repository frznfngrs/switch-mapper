# Switch Mapper

A Python application for mapping and visualizing Cisco Nexus 9K switch connections, including server connections identified through BMC/iLO interfaces.

## Features

- Queries Nexus switches via NX-API or SSH
- Discovers switch-to-switch connections using CDP and LLDP
- Identifies server connections by cross-referencing MAC addresses with BMC/iLO data
- Supports both HPE iLO and Dell iDRAC BMC interfaces
- Generates visual network diagrams using GraphViz
- Provides detailed text reports of all connections

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Install GraphViz (required for diagram generation):

For Windows:
```bash
winget install graphviz
```

For macOS:
```bash
brew install graphviz
```

For Linux:
```bash
sudo apt-get install graphviz  # Debian/Ubuntu
sudo yum install graphviz      # RHEL/CentOS
```

## Configuration

Create a `config.yaml` file with your switch and BMC details:

```yaml
switches:
  - hostname: "nexus9k-1"
    ip: "192.168.1.1"
    username: "admin"
    password: "your-password"
    use_nxapi: true
    port: 80

bmcs:
  - ip: "192.168.1.100"
    username: "admin"
    password: "your-password"
    type: "ilo"  # or "idrac"
```

## Usage

Run the mapper with default settings:
```bash
python -m switch_mapper
```

Specify a custom config file and output location:
```bash
python -m switch_mapper -c /path/to/config.yaml -o /path/to/output
```

### Command Line Options

- `-c, --config`: Path to configuration file (default: config.yaml)
- `-o, --output`: Output file base name without extension (default: network_diagram)

## Output

The application generates two output files:
1. A PNG diagram showing the network topology (network_diagram.png)
2. A text report with detailed connection information (network_diagram_report.txt)

### Sample Diagram Output

The generated diagram will show:
- Switches in light blue boxes
- Servers in light green boxes
- Unknown devices in gray boxes
- Connection details including interface names, MAC addresses, and protocols

### Sample Text Report Output

```
Network Connection Report
==================================================

Switch: nexus9k-1
------------------------------

  Connected Switches:
    Eth1/1: nexus9k-2 [CDP]
    Eth1/2: nexus9k-3 [LLDP]

  Connected Servers:
    Eth1/10: server1.example.com (MAC: 00:11:22:33:44:55) 
    Eth1/11: server2.example.com (MAC: 66:77:88:99:AA:BB)

  Unknown Devices:
    Eth1/20: Unknown Device (MAC: CC:DD:EE:FF:00:11)
```

## Architecture

The application is structured into several main components:

- `config.py`: Configuration management and validation
- `nxapi_client.py`: Interface with Nexus switches
- `bmc_client.py`: Interface with BMC/iLO systems
- `mapper.py`: Core mapping and diagram generation logic

## Error Handling

The application includes robust error handling for:
- Network connectivity issues
- Authentication failures
- Invalid configuration
- API response parsing
- Diagram generation failures

Errors are logged with appropriate context for troubleshooting.

## Security Notes

- Secure your config.yaml file as it contains sensitive credentials
- Consider using environment variables for credentials in production
- The application disables SSL verification for BMC connections due to common self-signed certificates
- Use dedicated service accounts with minimum required privileges

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details.
