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
        self.base_url = f"http://{host}:{port}/ins"
        self.headers = {
            'content-type': 'application/json'
        }

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
            response = requests.post(
                self.base_url,
                data=json.dumps(payload),
                headers=self.headers,
                auth=(self.username, self.password),
                verify=False
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
            if isinstance(response['ins_api']['outputs']['output'], list):
                neighbor_data = response['ins_api']['outputs']['output'][0]['body']
            else:
                neighbor_data = response['ins_api']['outputs']['output']['body']

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
            if isinstance(response['ins_api']['outputs']['output'], list):
                neighbor_data = response['ins_api']['outputs']['output'][0]['body']
            else:
                neighbor_data = response['ins_api']['outputs']['output']['body']

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
            if isinstance(response['ins_api']['outputs']['output'], list):
                mac_data = response['ins_api']['outputs']['output'][0]['body']
            else:
                mac_data = response['ins_api']['outputs']['output']['body']

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
            if isinstance(response['ins_api']['outputs']['output'], list):
                interface_data = response['ins_api']['outputs']['output'][0]['body']
            else:
                interface_data = response['ins_api']['outputs']['output']['body']

            for interface in interface_data.get('TABLE_interface', {}).get('ROW_interface', []):
                interfaces[interface.get('interface', '')] = interface.get('state', '')

        except (KeyError, AttributeError) as e:
            print(f"Error parsing interface status: {str(e)}")

        return interfaces
