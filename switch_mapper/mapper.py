from typing import Dict, List, Optional
import graphviz
from .config import Config, SwitchConfig, BMCConfig
from .nxapi_client import NXAPIClient, PortConnection
from .bmc_client import create_bmc_client

class SwitchMapper:
    def __init__(self, config_file: str = 'config.yaml'):
        self.config = Config(config_file)
        self.switch_connections: Dict[str, List[PortConnection]] = {}
        self.bmc_mac_to_hostname: Dict[str, str] = {}

    def gather_switch_data(self):
        """Gather data from all configured switches"""
        for switch_config in self.config.switches:
            client = NXAPIClient(
                switch_config.ip,
                switch_config.username,
                switch_config.password,
                switch_config.port
            )

            connections = []
            # Get CDP and LLDP neighbors
            connections.extend(client.get_cdp_neighbors())
            connections.extend(client.get_lldp_neighbors())
            
            # Get MAC address table entries
            mac_entries = client.get_mac_address_table()
            
            # Add interface status
            interface_status = client.get_interface_status()
            
            # Merge MAC entries with existing connections
            for entry in mac_entries:
                # Check if we already have this interface from CDP/LLDP
                existing = next(
                    (c for c in connections if c.interface == entry.interface),
                    None
                )
                if existing:
                    existing.mac_address = entry.mac_address
                else:
                    connections.append(entry)

            self.switch_connections[switch_config.hostname] = connections

    def gather_bmc_data(self):
        """Gather MAC address data from BMC/iLO interfaces"""
        for bmc_config in self.config.bmcs:
            try:
                client = create_bmc_client(
                    bmc_config.ip,
                    bmc_config.username,
                    bmc_config.password,
                    bmc_config.type
                )
                
                network_info = client.get_network_info()
                hostname = network_info['hostname']
                
                # Map each MAC address to the hostname
                for interface in network_info['interfaces']:
                    if interface['mac_address']:
                        self.bmc_mac_to_hostname[interface['mac_address']] = hostname
                        
            except Exception as e:
                print(f"Error gathering BMC data from {bmc_config.ip}: {str(e)}")

    def update_unknown_devices(self):
        """Update unknown devices with hostname information from BMCs"""
        for switch_hostname, connections in self.switch_connections.items():
            for conn in connections:
                if conn.device_type == 'unknown' and conn.mac_address:
                    # Check if we have hostname information for this MAC
                    hostname = self.bmc_mac_to_hostname.get(conn.mac_address)
                    if hostname:
                        conn.connected_device = hostname
                        conn.device_type = 'server'

    def generate_diagram(self, output_file: str = 'network_diagram') -> str:
        """Generate network diagram using graphviz"""
        dot = graphviz.Digraph(comment='Network Diagram')
        dot.attr(rankdir='TB')
        
        # Set node styles
        dot.attr('node', shape='box')
        
        # Add switches
        for switch_hostname in self.switch_connections.keys():
            dot.node(switch_hostname, f"{switch_hostname}\\nNexus 9K", style='filled', fillcolor='lightblue')
        
        # Add connections and servers
        for switch_hostname, connections in self.switch_connections.items():
            for conn in connections:
                if not conn.connected_device:
                    continue
                
                # Format connection label
                label = f"{conn.interface}"
                if conn.mac_address:
                    label += f"\\nMAC: {conn.mac_address}"
                if conn.protocol:
                    label += f"\\n{conn.protocol}"
                
                # Add node and edge based on device type
                if conn.device_type == 'switch':
                    # Only add edge between switches
                    dot.edge(switch_hostname, conn.connected_device, label=label)
                elif conn.device_type == 'server':
                    # Add server node and connection
                    dot.node(conn.connected_device, conn.connected_device, style='filled', fillcolor='lightgreen')
                    dot.edge(switch_hostname, conn.connected_device, label=label)
                else:
                    # Add unknown device
                    node_name = f"unknown_{conn.interface}"
                    dot.node(node_name, f"Unknown Device\\n{conn.mac_address if conn.mac_address else ''}", style='filled', fillcolor='lightgray')
                    dot.edge(switch_hostname, node_name, label=label)
        
        # Save diagram
        try:
            dot.render(output_file, format='png', cleanup=True)
            return f"{output_file}.png"
        except Exception as e:
            print(f"Error generating diagram: {str(e)}")
            return ""

    def generate_text_report(self) -> str:
        """Generate text-based report of connections"""
        report = []
        report.append("Network Connection Report")
        report.append("=" * 50)
        
        for switch_hostname, connections in self.switch_connections.items():
            report.append(f"\nSwitch: {switch_hostname}")
            report.append("-" * 30)
            
            # Group by device type
            switches = []
            servers = []
            unknown = []
            
            for conn in connections:
                line = f"  {conn.interface}: "
                if conn.connected_device:
                    line += f"{conn.connected_device} "
                if conn.mac_address:
                    line += f"(MAC: {conn.mac_address}) "
                if conn.protocol:
                    line += f"[{conn.protocol}]"
                
                if conn.device_type == 'switch':
                    switches.append(line)
                elif conn.device_type == 'server':
                    servers.append(line)
                else:
                    unknown.append(line)
            
            if switches:
                report.append("\n  Connected Switches:")
                report.extend(switches)
            
            if servers:
                report.append("\n  Connected Servers:")
                report.extend(servers)
            
            if unknown:
                report.append("\n  Unknown Devices:")
                report.extend(unknown)
        
        return "\n".join(report)

    def map_network(self, output_file: str = 'network_diagram') -> tuple[str, str]:
        """Map the network and generate both diagram and text report"""
        try:
            self.gather_switch_data()
            self.gather_bmc_data()
            self.update_unknown_devices()
            
            diagram_path = self.generate_diagram(output_file)
            text_report = self.generate_text_report()
            
            return diagram_path, text_report
            
        except Exception as e:
            print(f"Error mapping network: {str(e)}")
            return "", ""
