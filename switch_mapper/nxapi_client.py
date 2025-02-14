import requests
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
import time

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

    def get_lldp_neighbors(self) -> List[PortConnection]:
        """Get LLDP neighbor information"""
        response = self._send_request(["show lldp neighbors detail"])
        neighbors = []

        try:
            # Parse NX-API response
            if isinstance(response, dict):
                result = response
            else:
                result = response.json()

            neighbor_data = {}
            if 'ins_api' in result:
                # Handle legacy NX-API format
                if isinstance(result['ins_api']['outputs']['output'], list):
                    neighbor_data = result['ins_api']['outputs']['output'][0]['body']
                else:
                    neighbor_data = result['ins_api']['outputs']['output']['body']
            elif 'result' in result:
                # Handle JSON-RPC format
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
        """Get MAC address table information in chunks by interface"""
        mac_entries = []
        chunk_size = 8  # Number of interfaces per chunk

        try:
            # First get all interfaces
            interface_status = self.get_interface_status()
            interfaces = list(interface_status.keys())
            print(f"Found {len(interfaces)} interfaces to process in chunks")

            # Process interfaces in chunks
            for i in range(0, len(interfaces), chunk_size):
                interface_chunk = interfaces[i:i+chunk_size]
                print(f"Processing interfaces {i+1} to {min(i+chunk_size, len(interfaces))}")
                
                # Build command for this chunk of interfaces
                interface_params = " interface ".join(interface_chunk)
                cmd = f"show mac address-table interface {interface_params}"
                
                try:
                    response = self._send_request([cmd])
                    
                    # Parse response
                    if isinstance(response, dict):
                        result = response
                    else:
                        result = response.json()

                    mac_data = {}
                    if 'ins_api' in result:
                        # Handle legacy NX-API format
                        if isinstance(result['ins_api']['outputs']['output'], list):
                            mac_data = result['ins_api']['outputs']['output'][0]['body']
                        else:
                            mac_data = result['ins_api']['outputs']['output']['body']
                    elif 'result' in result:
                        # Handle JSON-RPC format
                        output = result.get('result', {})
                        if isinstance(output, list):
                            mac_data = output[0].get('body', {})
                        else:
                            mac_data = output.get('body', {})

                    # Process MAC entries for this chunk
                    entries = mac_data.get('TABLE_mac_address', {}).get('ROW_mac_address', [])
                    if not isinstance(entries, list):
                        entries = [entries]

                    for entry in entries:
                        if entry:  # Skip empty entries
                            mac_entries.append(PortConnection(
                                interface=entry.get('disp_port', ''),
                                connected_device=None,  # MAC table doesn't provide hostname
                                mac_address=entry.get('disp_mac_addr', ''),
                                protocol=None,
                                device_type='unknown'
                            ))

                    print(f"Found {len(entries)} MAC entries in current chunk")
                    
                    # Add delay between chunks to respect rate limits
                    if i + chunk_size < len(interfaces):  # Don't sleep after the last chunk
                        time.sleep(1)  # 1 second delay between chunks

                except Exception as chunk_error:
                    print(f"Error processing interface chunk {interface_chunk}: {str(chunk_error)}")
                    continue  # Continue with next chunk even if this one fails

        except (KeyError, AttributeError) as e:
            print(f"Error in MAC address table collection: {str(e)}")

        print(f"Total MAC entries collected: {len(mac_entries)}")
        return mac_entries

    def get_interface_status(self) -> Dict[str, str]:
        """Get interface status information"""
        response = self._send_request(["show interface status"])
        interfaces = {}

        try:
            # Parse NX-API response
            if isinstance(response, dict):
                result = response
            else:
                result = response.json()

            interface_data = {}
            if 'ins_api' in result:
                # Handle legacy NX-API format
                if isinstance(result['ins_api']['outputs']['output'], list):
                    interface_data = result['ins_api']['outputs']['output'][0]['body']
                else:
                    interface_data = result['ins_api']['outputs']['output']['body']
            elif 'result' in result:
                # Handle JSON-RPC format
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
