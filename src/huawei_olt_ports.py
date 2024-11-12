#!/usr/bin/env python3
import paramiko
import argparse
import json
import sys
import re
import time
from typing import Dict, List

class OLTPortsChecker:
    def __init__(self, host: str, username: str, password: str, verbose: bool = False):
        self.host = host
        self.username = username
        self.password = password
        self.verbose = verbose
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.channel = None
        
    def log(self, message: str) -> None:
        if self.verbose:
            print(f"VERBOSE: {message}", file=sys.stderr)
        
    def connect(self) -> None:
        try:
            self.client.connect(
                hostname=self.host,
                username=self.username,
                password=self.password,
                look_for_keys=False,
                allow_agent=False
            )
            
            self.channel = self.client.invoke_shell()
            time.sleep(2)
            self.channel.recv(4096)
            
            self.log(f"Successfully connected to {self.host}")
            
            # Entra em modo config
            self.channel.send('enable\n')
            time.sleep(1)
            self.channel.recv(4096)
            
            self.channel.send('config\n')
            time.sleep(1)
            
        except Exception as e:
            print(json.dumps({
                "error": {
                    "message": f"Failed to connect to {self.host}: {str(e)}",
                    "type": "ConnectionError"
                }
            }), file=sys.stderr)
            sys.exit(1)

    def execute_command(self, command: str) -> str:
        self.log(f"Executing command: {command}")
        
        self.channel.send(f"{command}\n")
        time.sleep(2)
        
        output = ""
        while True:
            if self.channel.recv_ready():
                chunk = self.channel.recv(4096).decode('utf-8')
                output += chunk
                
                if "---- More" in chunk:
                    self.channel.send(' ')
                    time.sleep(1)
                elif any(prompt in chunk for prompt in ['(config)#', '>', '#']):
                    break
            else:
                time.sleep(0.1)
                if not self.channel.recv_ready():
                    break
        
        return output

    def get_slots_and_ports(self) -> Dict:
        """Get all GPON slots and their ports."""
        command = 'display board 0'
        output = self.execute_command(command)
        self.log(f"BOARD OUTPUT:\n{output}")
        
        result = {
            'olt_info': {
                'host': self.host,
                'slots': []
            }
        }
        
        # Procura slots com H805GPFD
        slot_pattern = re.compile(r'^\s*(\d+)\s+H805GPFD\s+(\w+)\s*', re.MULTILINE)
        slot_matches = list(slot_pattern.finditer(output))
        
        # Verifica se todos os slots foram encontrados
        self.log(f"Found {len(slot_matches)} GPON slots")
        
        for match in slot_matches:
            slot_id = match.group(1)
            state = match.group(2)
            self.log(f"Processing slot {slot_id} with state {state}")
            
            if state.lower() == 'normal':
                # Para cada slot GPFD, verifica as portas
                interface_cmd = f'interface gpon 0/{slot_id}'
                self.execute_command(interface_cmd)
                
                # Coleta estado das portas com all
                port_output = self.execute_command('display port state all')
                self.log(f"PORT OUTPUT for slot {slot_id}:\n{port_output}")
                
                ports = []
                # Ajusta o pattern para capturar linha F/S/P
                port_pattern = re.compile(
                    r'F/S/P\s+0/\d+/(\d+)\s*\n'
                    r'\s*Optical Module status\s+(\w+)\s*\n'
                    r'\s*Port state\s+(\w+)\s*\n'
                    r'\s*Laser state\s+(\w+)\s*\n'
                    r'\s*Available bandwidth\(Kbps\)\s+(\d+)\s*\n'
                    r'\s*Temperature\(C\)\s+(\d+)\s*\n'
                    r'(?:[^\n]*\n)*?'  # Skip lines until TX power
                    r'\s*TX power\(dBm\)\s+([-\d.]+)',
                    re.MULTILINE
                )
                
                for port_match in port_pattern.finditer(port_output):
                    port_id = port_match.group(1)
                    module_status = port_match.group(2)
                    port_state = port_match.group(3)
                    laser_state = port_match.group(4)
                    bandwidth = port_match.group(5)
                    temperature = port_match.group(6)
                    tx_power = port_match.group(7)
                    
                    port_info = {
                        'id': port_id,
                        'module_status': module_status,
                        'state': port_state,
                        'laser_state': laser_state,
                        'tx_power': f"{tx_power} dBm",
                        'bandwidth': f"{bandwidth} Kbps",
                        'temperature': {
                            'value': int(temperature),
                            'unit': 'C',
                            'formatted': f"{temperature}°C"
                        }
                    }
                    
                    ports.append(port_info)
                
                # Ordena as portas por ID
                ports.sort(key=lambda x: int(x['id']))
                
                slot_info = {
                    'id': slot_id,
                    'type': 'H805GPFD',
                    'state': state,
                    'ports': ports
                }
                result['olt_info']['slots'].append(slot_info)
                
                # Sai da interface GPON
                self.execute_command('quit')
            else:
                self.log(f"Skipping slot {slot_id} because state is {state}")
        
        # Ordena os slots por ID
        result['olt_info']['slots'].sort(key=lambda x: int(x['id']))
        
        return result

    def close(self) -> None:
        if self.channel:
            self.channel.close()
        self.client.close()
        self.log("Connection closed")

def main():
    parser = argparse.ArgumentParser(description='Huawei OLT Ports Checker')
    parser.add_argument('--host', required=True, help='OLT hostname or IP')
    parser.add_argument('--username', required=True, help='SSH username')
    parser.add_argument('--password', required=True, help='SSH password')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    checker = OLTPortsChecker(
        host=args.host,
        username=args.username,
        password=args.password,
        verbose=args.verbose
    )
    
    try:
        checker.connect()
        inventory = checker.get_slots_and_ports()
        print(json.dumps(inventory, indent=2))
        
    except Exception as e:
        print(json.dumps({
            "error": {
                "message": str(e),
                "type": e.__class__.__name__
            }
        }), file=sys.stderr)
        sys.exit(1)
    finally:
        checker.close()

if __name__ == '__main__':
    main()