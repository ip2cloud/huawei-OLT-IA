#!/usr/bin/env python3
import paramiko
import argparse
import json
import sys
import re
import time
from datetime import datetime
from typing import List, Dict, Optional

class ONTStatusChecker:
    def __init__(self, host: str, username: str, password: str, verbose: bool = False):
        """Initialize SSH connection to the Huawei OLT."""
        self.host = host
        self.username = username
        self.password = password
        self.verbose = verbose
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.channel = None
        
    def log(self, message: str) -> None:
        """Log messages only when verbose mode is enabled."""
        if self.verbose:
            print(f"VERBOSE: {message}", file=sys.stderr)
        
    def connect(self) -> None:
        """Establish SSH connection to the OLT."""
        try:
            self.client.connect(
                hostname=self.host,
                username=self.username,
                password=self.password,
                look_for_keys=False,
                allow_agent=False
            )
            
            self.channel = self.client.invoke_shell()
            time.sleep(2)  # Wait for shell to initialize
            self.channel.recv(4096)
            
            self.log(f"Successfully connected to {self.host}")
            self._setup_session()
            
        except Exception as e:
            print(json.dumps({
                "error": {
                    "message": f"Failed to connect to {self.host}: {str(e)}",
                    "type": "ConnectionError"
                }
            }), file=sys.stderr)
            sys.exit(1)
            
    def _setup_session(self) -> None:
        """Setup the session with correct configuration mode."""
        self.channel.send('enable\n')
        time.sleep(1)
        self.channel.recv(4096)
        
        self.channel.send('config\n')
        time.sleep(1)

        self.channel.send('mmi-mode original-output\n')
        time.sleep(1)
        
        self.log("Entered configuration mode")

    def execute_command(self, command: str) -> str:
        """Execute command on the OLT and return output."""
        self.log(f"Executing command: {command}")
        
        # Garante que números em comandos específicos tenham espaços
        if 'optical-info' in command:
            parts = command.split()
            if len(parts) >= 2:
                # Reconstrói o comando garantindo espaços
                command = ' '.join(parts[:-2] + [parts[-2], parts[-1]])
        
        self.channel.send(f"{command}\n")
        time.sleep(2)
        
        output = ""
        while True:
            if self.channel.recv_ready():
                chunk = self.channel.recv(4096).decode('utf-8')
                output += chunk
                
                # Se encontrar prompt de More, envia espaço
                if "---- More" in chunk:
                    self.channel.send(' ')
                    time.sleep(1)
                # Aguarda até ver o prompt de comando
                elif any(prompt in chunk for prompt in ['(config)#', '(config-if-gpon-', '>', '#']):
                    break
            else:
                time.sleep(0.1)
                if not self.channel.recv_ready():
                    break
        
        return output

    def parse_date(self, date_str: str) -> str:
        """Parse date from OLT format to ISO format."""
        if not date_str or date_str == '-':
            return ''
            
        try:
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M:%S%z',
                '%Y-%m-%d %H:%M:%S+%f',
                '%Y-%m-%d %H:%M:%S-%f',
                '%Y%m%d%H%M%S',
                '%Y-%m-%d'
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(date_str.strip(), fmt)
                    return dt.isoformat()
                except ValueError:
                    continue
                    
            return date_str
        except Exception:
            return date_str

    def check_single_ont_status(self, frame: str, slot: str, port: str, ont: str) -> Dict:
        """Check status of a single ONT."""
        # Informações básicas da ONT
        info_command = f"display ont info {frame} {slot} {port} {ont}"
        info_output = self.execute_command(info_command)
        self.log(f"INFO OUTPUT:\n{info_output}")
        
        # Entra na interface GPON
        gpon_interface = f"interface gpon {frame}/{slot}"
        self.execute_command(gpon_interface)
        self.log(f"Entered GPON interface: {gpon_interface}")
        
        # Garante espaço entre parâmetros do comando optical-info
        optical_command = f"display ont optical-info {port} {ont}"
        self.channel.send(f"{optical_command}\n")
        time.sleep(2)
        optical_output = ""
        
        while self.channel.recv_ready():
            chunk = self.channel.recv(4096).decode('utf-8')
            optical_output += chunk
            if ")#" in chunk:  # Aguarda o prompt completo
                break
            time.sleep(0.1)
        
        self.log(f"OPTICAL OUTPUT:\n{optical_output}")

        # Sai da interface GPON após optical-info
        self.execute_command("quit")

        # Entra novamente na interface GPON para version summary
        self.execute_command(gpon_interface)
        self.log(f"Entered GPON interface for version: {gpon_interface}")
        
        # Garante espaço entre parâmetros do comando version (mesma abordagem do optical-info)
        version_command = f"display ont version {port} {ont}"
        self.channel.send(f"{version_command}\n")
        
        time.sleep(2)
        
        version_output = ""
        
        while self.channel.recv_ready():
            chunk = self.channel.recv(4096).decode('utf-8')
            version_output += chunk
            if ")#" in chunk:  # Aguarda o prompt completo
                break
            time.sleep(0.1)
        
        self.log(f"VERSION OUTPUT:\n{version_output}")
        
        # Retorna para o modo config
        self.execute_command("quit")
        
        status_info = {
            'ont_info': {
                'frame': frame,
                'slot': slot,
                'port': port,
                'ont_id': ont,
                'serial_number': '',
                'description': '',
                'status': {
                    'run_state': 'OFFLINE',
                    'control_flag': '',
                    'config_state': '',
                    'match_state': ''
                },
                'metrics': {
                    'distance': '',
                    'memory': '',
                    'cpu': '',
                    'temperature': '',
                    'online_duration': '',
                    'optical': {
                        'rx': '',
                        'tx': '',
                        'voltage': '',
                        'current': '',
                        'temperature': ''
                    }
                },
                'events': {
                    'last_down': {
                        'cause': '',
                        'time': ''
                    },
                    'last_up': {
                        'time': ''
                    },
                    'last_dying_gasp': {
                        'time': ''
                    },
                    'last_event': {
                        'type': '',
                        'cause': ''
                    }
                },
                'authentication': {
                    'type': '',
                    'mode': '',
                    'work_mode': ''
                },
                'version': {
                    'ont_version': '',
                    'equipment_id': '',
                    'software_version': ''
                }
            }
        }
        
        # Verifica se a ONT existe
        if 'The ONT does not exist' in info_output:
            return {
                'ont_info': {
                    'frame': frame,
                    'slot': slot,
                    'port': port,
                    'ont_id': ont,
                    'status': {
                        'run_state': 'NOT_EXISTS'
                    }
                }
            }
        
        # Status patterns baseados na documentação
        patterns = {
            'run_state': r'Run state\s*:\s*(\w+)',
            'control_flag': r'Control flag\s*:\s*(\w+)',
            'config_state': r'Config state\s*:\s*(\w+)',
            'match_state': r'Match state\s*:\s*(\w+)',
            'serial': r'SN\s*:\s*([A-Za-z0-9]+)',
            'description': r'Description\s*:\s*([^\r\n]+)',
            'distance': r'ONT distance\(m\)\s*:\s*(\d+)',
            'auth_type': r'Authentic type\s*:\s*([^\r\n]+)',
            'mgmt_mode': r'Management mode\s*:\s*([^\r\n]+)',
            'work_mode': r'Software work mode\s*:\s*([^\r\n]+)',
            'memory': r'Memory occupation\s*:\s*(\d+%)',
            'cpu': r'CPU occupation\s*:\s*(\d+%)',
            'temperature': r'Temperature\s*:\s*(\d+)\(C\)',
            'last_down_cause': r'Last down cause\s*:\s*([^\r\n]+)',
            'last_up_time': r'Last up time\s*:\s*([^\r\n]+)',
            'last_down_time': r'Last down time\s*:\s*([^\r\n]+)',
            'last_dying_gasp': r'Last dying gasp time\s*:\s*([^\r\n]+)',
            'online_duration': r'ONT online duration\s*:\s*([^\r\n]+)'
        }
        
        # Extract all basic information
        for key, pattern in patterns.items():
            match = re.search(pattern, info_output, re.IGNORECASE)
            if match and match.group(1).strip() not in ['-', '']:
                value = match.group(1).strip()
                if key == 'run_state':
                    status_info['ont_info']['status']['run_state'] = value.upper()
                elif key == 'control_flag':
                    status_info['ont_info']['status']['control_flag'] = value
                elif key == 'config_state':
                    status_info['ont_info']['status']['config_state'] = value
                elif key == 'match_state':
                    status_info['ont_info']['status']['match_state'] = value
                elif key == 'serial':
                    status_info['ont_info']['serial_number'] = value
                elif key == 'description':
                    status_info['ont_info']['description'] = value
                elif key == 'distance':
                    status_info['ont_info']['metrics']['distance'] = f"{value}m"
                elif key == 'memory':
                    status_info['ont_info']['metrics']['memory'] = value
                elif key == 'cpu':
                    status_info['ont_info']['metrics']['cpu'] = value
                elif key == 'temperature':
                    status_info['ont_info']['metrics']['temperature'] = f"{value}°C"
                elif key == 'online_duration':
                    status_info['ont_info']['metrics']['online_duration'] = value
                elif key == 'auth_type':
                    status_info['ont_info']['authentication']['type'] = value
                elif key == 'mgmt_mode':
                    status_info['ont_info']['authentication']['mode'] = value
                elif key == 'work_mode':
                    status_info['ont_info']['authentication']['work_mode'] = value
                elif key == 'last_down_cause':
                    status_info['ont_info']['events']['last_down']['cause'] = value
                elif key in ['last_up_time', 'last_down_time', 'last_dying_gasp']:
                    event_type = key.replace('_time', '')
                    time_value = self.parse_date(value)
                    status_info['ont_info']['events'][event_type]['time'] = time_value
        
        # Parse optical info
        optical_patterns = {
            'rx_power': r'Rx optical power\(dBm\)\s*:\s*([-\d.]+)',
            'tx_power': r'Tx optical power\(dBm\)\s*:\s*([-\d.]+)',
            'olt_rx_power': r'OLT Rx ONT optical power\(dBm\)\s*:\s*([-\d.]+)',
            'voltage': r'Voltage\(V\)\s*:\s*([-\d.]+)',
            'bias_current': r'Bias current\s*:\s*([-\d.]+)',
            'temperature': r' Temperature\(C\)\s*:\s*([-\d.]+)'
        }
        
        if optical_output and 'Unknown command' not in optical_output:
            optical_data = {}
            for key, pattern in optical_patterns.items():
                match = re.search(pattern, optical_output, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    if key == 'rx_power':
                        optical_data['rx'] = f"{value} dBm"
                    elif key == 'tx_power':
                        optical_data['tx'] = f"{value} dBm"
                    elif key == 'olt_rx_power':
                        optical_data['olt_rx'] = f"{value} dBm"
                    elif key == 'voltage':
                        optical_data['voltage'] = f"{value} V"
                    elif key == 'bias_current':
                        optical_data['current'] = f"{value} mA"
                    elif key == 'temperature':
                        optical_data['temperature'] = f"{value} °C"
                        
            if optical_data:
                status_info['ont_info']['metrics']['optical'] = optical_data
        
        # Parse version info
        version_patterns = {
            'ont_version': r'ONT\s+[Vv]ersion\s*:\s*([^\r\n]+)',
            'equipment_id': r'Equipment-ID\s*:\s*([^\r\n]+)',
            'software_version': r'[Mm]ain\s+[Ss]oftware\s+[Vv]ersion\s*:\s*([^\r\n]+)'
        }
        
        if version_output and 'Unknown command' not in version_output:
            version_data = {}
            for key, pattern in version_patterns.items():
                match = re.search(pattern, version_output, re.IGNORECASE)
                if match and match.group(1).strip() not in ['-', '']:
                    version_data[key] = match.group(1).strip()
                    
            if version_data:
                status_info['ont_info']['version'] = version_data
        
        # Determine last event
        events_times = {
            'up': status_info['ont_info']['events']['last_up'].get('time', ''),
            'down': status_info['ont_info']['events']['last_down'].get('time', ''),
            'dying_gasp': status_info['ont_info']['events'].get('last_dying_gasp', {}).get('time', '')
        }
        
        latest_event = max(
            [(time_str, event_type) for event_type, time_str in events_times.items() if time_str],
            default=(None, None),
            key=lambda x: x[0] if x[0] else ''
        )
        
        if latest_event[0]:
            if latest_event[1] == 'up':
                status_info['ont_info']['events']['last_event'] = {'type': 'up'}
            else:
                status_info['ont_info']['events']['last_event'] = {
                    'type': 'down',
                    'cause': status_info['ont_info']['events']['last_down']['cause']
                }
        
        # Clean up empty fields
        if not status_info['ont_info']['metrics'].get('optical'):
            status_info['ont_info']['metrics'].pop('optical', None)
        
        if not status_info['ont_info'].get('version'):
            status_info['ont_info'].pop('version', None)
        
        return status_info


    def check_batch_ont_status(self, frame: str, slot: str, onts: List[Dict]) -> List[Dict]:
        """Check status of multiple ONTs."""
        results = []
        for ont_info in onts:
            status = self.check_single_ont_status(
                frame=frame,
                slot=slot,
                port=str(ont_info['port']),
                ont=str(ont_info['ont'])
            )
            results.append(status)
        return results

    def close(self) -> None:
        """Close SSH connection."""
        if self.channel:
            self.channel.close()
        self.client.close()
        self.log("Connection closed")

def clean_dict(d: Dict) -> Dict:
    """Remove empty values from dictionary."""
    if not isinstance(d, dict):
        return d
        
    cleaned = {}
    for k, v in d.items():
        if isinstance(v, dict):
            v = clean_dict(v)
            if v:  # only add if non-empty
                cleaned[k] = v
        elif v not in (None, "", {}, []):
            cleaned[k] = v
    return cleaned

def handle_output(results: List[Dict]) -> None:
    """Format and print the results."""
    cleaned_results = [clean_dict(result) for result in results if result is not None]
    if not cleaned_results:
        cleaned_results = [{
            "error": {
                "message": "No valid data received from OLT",
                "type": "DataError"
            }
        }]
    print(json.dumps(cleaned_results, indent=2, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description='Huawei ONT Status Checker')
    parser.add_argument('--mode', choices=['single', 'batch'], required=True,
                      help='Operation mode: single ONT or batch')
    parser.add_argument('--host', required=True, help='OLT hostname or IP')
    parser.add_argument('--frame', required=True, help='Frame number')
    parser.add_argument('--slot', required=True, help='Slot number')
    parser.add_argument('--port', help='Port number (required for single mode)')
    parser.add_argument('--ont', help='ONT ID (required for single mode)')
    parser.add_argument('--onts', help='JSON array of ONTs (required for batch mode)')
    parser.add_argument('--username', required=True, help='SSH username')
    parser.add_argument('--password', required=True, help='SSH password')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    if args.mode == 'single' and (not args.port or not args.ont):
        parser.error("Single mode requires --port and --ont arguments")
    elif args.mode == 'batch' and not args.onts:
        parser.error("Batch mode requires --onts argument")
    
    checker = ONTStatusChecker(
        host=args.host,
        username=args.username,
        password=args.password,
        verbose=args.verbose
    )
    
    try:
        checker.connect()
        
        if args.mode == 'single':
            result = checker.check_single_ont_status(
                frame=args.frame,
                slot=args.slot,
                port=args.port,
                ont=args.ont
            )
            results = [result]
        else:  # batch mode
            onts = json.loads(args.onts)
            results = checker.check_batch_ont_status(
                frame=args.frame,
                slot=args.slot,
                onts=onts
            )
        
        handle_output(results)
        
    except Exception as e:
        print(json.dumps({
            "error": {
                "message": str(e),
                "type": e.__class__.__name__
            }
        }, file=sys.stderr))
        sys.exit(1)
    finally:
        checker.close()

if __name__ == '__main__':
    main()