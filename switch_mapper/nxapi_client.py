import requests
import json
from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class PortConnection:
    interface: str
    connected_device: Optional[str]
    mac_address: Optional[str]
    protocol: Optional[str]  # CDP/LLDP
    device_type: str  # 'switch', 'server', 'unknown'

class NXAPIClient:
    def __init__(self, host: str, username: str, password: str, port: int = 80):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        protocol = "https" if port == 443 else "http"
        self.base_url = f"{protocol}://{host}:{port}/ins"
        self.headers = {
            'content-type': 'application/json-rpc'
        }
        # Disable SSL warnings for self-signed certificates
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _send_request(self, commands: List[str]) -> Dict:
        payload = {
            "ins_api": {
                "version": "1.0",
                "type": "cli_show",
                "chunk": "0",
                "sid": "sid",
                "input": "; ".join(commands),
                "output_format": "json"
            }
        }

        try:
            # Update payload format for JSON-RPC
            rpc_payload = {
                "jsonrpc": "2.0",
                "method": "cli",
                "params": {
                    "cmd": "; ".join(commands),
                    "version": 1
                },
                "id": 1
            }
            
            response = requests.post(
                self.base_url,
                data=json.dumps(rpc_payload),
                headers=self.headers,
                auth=(self.username, self.password),
                verify=False  # Required for self-signed certificates
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to switch: {str(e)}")

    def get_cdp_neighbors(self) -> List[PortConnection]:
        """Get CDP neighbor information"""
        response = self._send_request(["show cdp neighbors detail"])
        neighbors = []

        try:
            # Parse JSON-RPC response
            result = response.json()
            if 'error' in result:
                raise Exception(f"NX-API error: {result['error']['message']}")
                
            output = result.get('result', {})
            if isinstance(output, list):
                neighbor_data = output[0].get('body', {})
            else:
                neighbor_data = output.get('body', {})

            for neighbor in neighbor_data.get('TABLE_cdp_neighbor_detail_info', {}).get('ROW_cdp_neighbor_detail_info', []):
                neighbors.append(PortConnection(
                    interface=neighbor.get('intf_id', ''),
                    connected_device=neighbor.get('device_id', ''),
                    mac_address=None,  # CDP doesn't provide MAC
                    protocol='CDP',
                    device_type='switch' if 'N9K' in neighbor.get('platform_id', '') else 'unknown'
                ))

        except (KeyError, AttributeError) as e:
            print(f"Error parsing CDP data: {str(e)}")

        return neighbors

    def get_lldp_neighbors(self) -> List[PortConnection]:
        """Get LLDP neighbor information"""
        response = self._send_request(["show lldp neighbors detail"])
        neighbors = []

        try:
            # Parse JSON-RPC response
            result = response.json()
            if 'error' in result:
                raise Exception(f"NX-API error: {result['error']['message']}")
                
            output = result.get('result', {})
            if isinstance(output, list):
                neighbor_data = output[0].get('body', {})
            else:
                neighbor_data = output.get('body', {})

            for neighbor in neighbor_data.get('TABLE_nbor_detail', {}).get('ROW_nbor_detail', []):
                neighbors.append(PortConnection(
                    interface=neighbor.get('l_port_id', ''),
                    connected_device=neighbor.get('sys_name', ''),
                    mac_address=neighbor.get('chassis_id', None),
                    protocol='LLDP',
                    device_type='switch' if 'N9K' in neighbor.get('sys_desc', '') else 'unknown'
                ))

        except (KeyError, AttributeError) as e:
            print(f"Error parsing LLDP data: {str(e)}")

        return neighbors

    def get_mac_address_table(self) -> List[PortConnection]:
        """Get MAC address table information"""
        response = self._send_request(["show mac address-table"])
        mac_entries = []

        try:
            # Parse JSON-RPC response
            result = response.json()
            if 'error' in result:
                raise Exception(f"NX-API error: {result['error']['message']}")
                
            output = result.get('result', {})
            if isinstance(output, list):
                mac_data = output[0].get('body', {})
            else:
                mac_data = output.get('body', {})

            for entry in mac_data.get('TABLE_mac_address', {}).get('ROW_mac_address', []):
                mac_entries.append(PortConnection(
                    interface=entry.get('disp_port', ''),
                    connected_device=None,  # MAC table doesn't provide hostname
                    mac_address=entry.get('disp_mac_addr', ''),
                    protocol=None,
                    device_type='unknown'
                ))

        except (KeyError, AttributeError) as e:
            print(f"Error parsing MAC address table: {str(e)}")

        return mac_entries

    def get_interface_status(self) -> Dict[str, str]:
        """Get interface status information"""
        response = self._send_request(["show interface status"])
        interfaces = {}

        try:
            # Parse JSON-RPC response
            result = response.json()
            if 'error' in result:
                raise Exception(f"NX-API error: {result['error']['message']}")
                
            output = result.get('result', {})
            if isinstance(output, list):
                interface_data = output[0].get('body', {})
            else:
                interface_data = output.get('body', {})

            for interface in interface_data.get('TABLE_interface', {}).get('ROW_interface', []):
                interfaces[interface.get('interface', '')] = interface.get('state', '')

        except (KeyError, AttributeError) as e:
            print(f"Error parsing interface status: {str(e)}")

        return interfaces
