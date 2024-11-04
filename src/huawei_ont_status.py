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
        
        self.log("Entered configuration mode")

    def execute_command(self, command: str) -> str:
        """Execute command on the OLT and return output."""
        self.log(f"Executing command: {command}")
        
        self.channel.send(f"{command}\n")
        time.sleep(2)
        
        output = ""
        buffer = ""
        more_count = 0
        max_more = 10  # Limite máximo de "More" para evitar loop infinito
        
        while True:
            if self.channel.recv_ready():
                buffer = self.channel.recv(4096).decode('utf-8')
                output += buffer
            
            if "---- More" in buffer:
                more_count += 1
                if more_count > max_more:
                    break
                self.channel.send(' ')
                time.sleep(1)
            elif not self.channel.recv_ready():
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
        # Primeiro coleta informações básicas da ONT
        info_command = f"display ont info {frame} {slot} {port} {ont}"
        info_output = self.execute_command(info_command)
        
        # Depois coleta o histórico
        history_command = f"display ont history {frame} {slot} {port} {ont}"
        history_output = self.execute_command(history_command)
        
        # Coleta informações ópticas
        optical_command = f"display ont optical-info {frame} {slot} {port} {ont}"
        optical_output = ""
        
        # Tenta várias vezes coletar info óptica (às vezes precisa de mais de uma tentativa)
        for _ in range(3):
            optical_output = self.execute_command(optical_command)
            if "Optical" in optical_output:
                break
            time.sleep(1)
        
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
                    'temperature': '',
                    'optical': {
                        'rx_power': '',
                        'tx_power': '',
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
                    'last_event': {
                        'type': '',
                        'cause': ''
                    }
                },
                'authentication': {
                    'type': '',
                    'mode': ''
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
        
        # Status patterns
        patterns = {
            'run_state': r'Run state\s*:\s*(\w+)',
            'control_flag': r'Control flag\s*:\s*(\w+)',
            'config_state': r'Config state\s*:\s*(\w+)',
            'match_state': r'Match state\s*:\s*(\w+)',
            'serial': r'SN\s*:\s*(\w+)',
            'description': r'Description\s*:\s*(.+?)[\r\n]',
            'distance': r'ONT distance\(m\)\s*:\s*(\d+)',
            'auth_type': r'Authentic type\s*:\s*([^\r\n]+)',
            'mgmt_mode': r'Management mode\s*:\s*([^\r\n]+)',
            'last_down_time': r'Last down time\s*:\s*([^\r\n]+)',
            'last_down_cause': r'Last down cause\s*:\s*([^\r\n]+)',
            'last_up_time': r'Last up time\s*:\s*([^\r\n]+)'
        }
        
        # Extract all basic information
        for key, pattern in patterns.items():
            match = re.search(pattern, info_output + history_output, re.IGNORECASE)
            if match:
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
                elif key == 'auth_type':
                    status_info['ont_info']['authentication']['type'] = value
                elif key == 'mgmt_mode':
                    status_info['ont_info']['authentication']['mode'] = value
                elif key == 'last_down_time':
                    status_info['ont_info']['events']['last_down']['time'] = self.parse_date(value)
                elif key == 'last_down_cause':
                    status_info['ont_info']['events']['last_down']['cause'] = value
                elif key == 'last_up_time':
                    status_info['ont_info']['events']['last_up']['time'] = self.parse_date(value)
        
        # Eventos
        last_up_time = status_info['ont_info']['events']['last_up'].get('time', '')
        last_down_time = status_info['ont_info']['events']['last_down'].get('time', '')
        
        if last_up_time and last_down_time:
            try:
                up_dt = datetime.fromisoformat(last_up_time)
                down_dt = datetime.fromisoformat(last_down_time)
                if up_dt > down_dt:
                    status_info['ont_info']['events']['last_event'] = {
                        'type': 'up'
                    }
                else:
                    status_info['ont_info']['events']['last_event'] = {
                        'type': 'down',
                        'cause': status_info['ont_info']['events']['last_down']['cause']
                    }
            except ValueError:
                pass
        elif last_up_time:
            status_info['ont_info']['events']['last_event'] = {
                'type': 'up'
            }
        elif last_down_time:
            status_info['ont_info']['events']['last_event'] = {
                'type': 'down',
                'cause': status_info['ont_info']['events']['last_down']['cause']
            }
        
        # Optical patterns mais específicos
        optical_patterns = {
            'rx_power': r'Rx optical power\(dBm\)\s*:\s*([-\d.]+)',
            'tx_power': r'Tx optical power\(dBm\)\s*:\s*([-\d.]+)',
            'voltage': r'Voltage\(V\)\s*:\s*([-\d.]+)',
            'bias_current': r'Laser bias current\(mA\)\s*:\s*(\d+)',
            'temperature': r'Temperature\(C\)\s*:\s*(\d+)',
            'olt_rx_power': r'OLT Rx ONT optical power\(dBm\)\s*:\s*([-\d.]+)'
        }
        
        if optical_output:
            optical_data = {}
            for key, pattern in optical_patterns.items():
                match = re.search(pattern, optical_output, re.IGNORECASE | re.MULTILINE)
                if match:
                    value = match.group(1).strip()
                    if 'power' in key:
                        optical_data[key.replace('_power', '')] = f"{value} dBm"
                    elif key == 'voltage':
                        optical_data['voltage'] = f"{value} V"
                    elif key == 'bias_current':
                        optical_data['current'] = f"{value} mA"
                    elif key == 'temperature':
                        optical_data['temperature'] = f"{value} °C"
                    elif key == 'olt_rx_power':
                        optical_data['olt_rx'] = f"{value} dBm"
        
        if optical_data:
            status_info['ont_info']['metrics']['optical'] = optical_data

        # Clean up empty fields
        if not status_info['ont_info']['metrics'].get('optical'):
            status_info['ont_info']['metrics'].pop('optical', None)
        
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