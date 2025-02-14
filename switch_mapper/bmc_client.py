from abc import ABC, abstractmethod
import requests
from typing import Dict, List, Optional
import json
import urllib3

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class BMCClient(ABC):
    """Abstract base class for BMC/ILO clients"""
    
    @abstractmethod
    def get_network_info(self) -> Dict:
        """Get network information including MAC addresses"""
        pass

class ILOClient(BMCClient):
    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.session.auth = (username, password)
        self.base_url = f"https://{host}/redfish/v1"

    def _send_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict:
        """Send request to iLO REST API"""
        url = f"{self.base_url}/{endpoint}"
        try:
            if method == 'GET':
                response = self.session.get(url)
            elif method == 'POST':
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to iLO: {str(e)}")

    def get_network_info(self) -> Dict:
        """Get network information from iLO including MAC addresses"""
        try:
            # Get system and network data
            system_data = self._send_request('Systems/1')
            network_info = {
                'hostname': system_data.get('HostName', ''),
                'interfaces': []
            }

            # Try different known paths for network interfaces
            paths_to_try = [
                'Systems/1/BaseNetworkAdapter/1',  # Some iLO versions
                'Systems/1/EthernetInterfaces',    # Redfish standard
                'Systems/1/NetworkAdapters'        # Alternative path
            ]

            print(f"System data keys: {list(system_data.keys())}")  # Debug output

            # Check system data first
            if 'EthernetInterfaces' in system_data:
                eth_uri = system_data['EthernetInterfaces'].get('@odata.id', '')
                if eth_uri:
                    try:
                        eth_data = self._send_request(eth_uri.split('/redfish/v1/')[-1])
                        print(f"EthernetInterfaces data: {eth_data}")  # Debug output
                        for member in eth_data.get('Members', []):
                            member_uri = member.get('@odata.id', '')
                            if member_uri:
                                interface = self._send_request(member_uri.split('/redfish/v1/')[-1])
                                if interface.get('MACAddress'):
                                    network_info['interfaces'].append({
                                        'name': interface.get('Name', ''),
                                        'mac_address': interface.get('MACAddress', '').upper(),
                                        'status': interface.get('Status', {}).get('State', 'OK')
                                    })
                    except Exception as e:
                        print(f"Error accessing EthernetInterfaces: {str(e)}")

            # If no interfaces found, try direct paths
            if not network_info['interfaces']:
                for path in paths_to_try:
                    try:
                        data = self._send_request(path)
                        print(f"Trying path {path}: {list(data.keys())}")  # Debug output
                        
                        if 'Members' in data:
                            for member in data['Members']:
                                member_uri = member.get('@odata.id', '')
                                if member_uri:
                                    interface = self._send_request(member_uri.split('/redfish/v1/')[-1])
                                    if interface.get('MACAddress'):
                                        network_info['interfaces'].append({
                                            'name': interface.get('Name', ''),
                                            'mac_address': interface.get('MACAddress', '').upper(),
                                            'status': interface.get('Status', {}).get('State', 'OK')
                                        })
                    except Exception as e:
                        print(f"Error with path {path}: {str(e)}")
            
            return network_info
            
        except Exception as e:
            print(f"Error getting iLO network info: {str(e)}")
            return {'hostname': '', 'interfaces': []}

class IDRACClient(BMCClient):
    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.verify = False
        self.session.auth = (username, password)
        self.base_url = f"https://{host}/redfish/v1"

    def _send_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict:
        """Send request to iDRAC Redfish API"""
        url = f"{self.base_url}/{endpoint}"
        try:
            if method == 'GET':
                response = self.session.get(url)
            elif method == 'POST':
                response = self.session.post(url, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to connect to iDRAC: {str(e)}")

    def get_network_info(self) -> Dict:
        """Get network information from iDRAC including MAC addresses"""
        try:
            # Get system information
            system_data = self._send_request('Systems/System.Embedded.1')
            
            network_info = {
                'hostname': system_data.get('HostName', ''),
                'interfaces': []
            }
            
            # Get network interfaces
            ethernet_interfaces = self._send_request('Systems/System.Embedded.1/EthernetInterfaces')
            
            for interface in ethernet_interfaces.get('Members', []):
                interface_uri = interface.get('@odata.id', '')
                if interface_uri:
                    interface_data = self._send_request(interface_uri.split('/redfish/v1/')[-1])
                    network_info['interfaces'].append({
                        'name': interface_data.get('Name', ''),
                        'mac_address': interface_data.get('MacAddress', '').upper(),
                        'status': interface_data.get('Status', {}).get('State', 'Unknown')
                    })
            
            return network_info
            
        except Exception as e:
            print(f"Error getting iDRAC network info: {str(e)}")
            return {'hostname': '', 'interfaces': []}

def create_bmc_client(host: str, username: str, password: str, bmc_type: str) -> BMCClient:
    """Factory function to create appropriate BMC client"""
    if bmc_type.lower() == 'ilo':
        return ILOClient(host, username, password)
    elif bmc_type.lower() == 'idrac':
        return IDRACClient(host, username, password)
    else:
        raise ValueError(f"Unsupported BMC type: {bmc_type}")
