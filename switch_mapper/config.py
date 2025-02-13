import os
from dataclasses import dataclass
from typing import List, Dict
import yaml

@dataclass
class SwitchConfig:
    hostname: str
    ip: str
    username: str
    password: str
    use_nxapi: bool = True
    port: int = 80

@dataclass
class BMCConfig:
    ip: str
    username: str
    password: str
    type: str  # 'ilo' or 'idrac'

class Config:
    def __init__(self, config_file: str = 'config.yaml'):
        self.config_file = config_file
        self.switches: List[SwitchConfig] = []
        self.bmcs: List[BMCConfig] = []
        self.load_config()

    def load_config(self):
        if not os.path.exists(self.config_file):
            # Create default config if not exists
            self.create_default_config()
        
        with open(self.config_file, 'r') as f:
            config = yaml.safe_load(f)

        self.switches = [
            SwitchConfig(**switch) for switch in config.get('switches', [])
        ]
        self.bmcs = [
            BMCConfig(**bmc) for bmc in config.get('bmcs', [])
        ]

    def create_default_config(self):
        default_config = {
            'switches': [{
                'hostname': 'nexus9k-1',
                'ip': '192.168.1.1',
                'username': 'admin',
                'password': 'password',
                'use_nxapi': True,
                'port': 80
            }],
            'bmcs': [{
                'ip': '192.168.1.100',
                'username': 'admin',
                'password': 'password',
                'type': 'ilo'
            }]
        }

        with open(self.config_file, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False)
