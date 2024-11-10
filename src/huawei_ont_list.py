import paramiko
import argparse
import json
import sys
import re
import time
from typing import List, Dict, Optional

class ONTListChecker:
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
            time.sleep(2)
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
        while True:
            if self.channel.recv_ready():
                chunk = self.channel.recv(4096).decode('utf-8')
                output += chunk
                
                if "---- More" in chunk:
                    self.channel.send(' ')
                    time.sleep(1)
                elif any(prompt in chunk for prompt in ['(config)#', '(config-if-gpon-', '>', '#']):
                    break
            else:
                time.sleep(0.1)
                if not self.channel.recv_ready():
                    break
        
        return output

    def check_port_onts(self, frame: str, slot: str, port: str) -> Dict:
        """Check all ONTs in a specific port."""
        # Comando para listar ONTs da porta
        list_command = f"display ont info summary {frame}/{slot}/{port}"
        list_output = self.execute_command(list_command)
        self.log(f"LIST OUTPUT:\n{list_output}")

        port_info = {
            'port_info': {
                'frame': frame,
                'slot': slot,
                'port': port,
                'total_onts': 0,
                'online_onts': 0,
                'onts': []
            }
        }

        # Parse total ONTs information
        total_pattern = r'the total of ONTs are:\s*(\d+),\s*online:\s*(\d+)'
        total_match = re.search(total_pattern, list_output)
        if total_match:
            port_info['port_info']['total_onts'] = int(total_match.group(1))
            port_info['port_info']['online_onts'] = int(total_match.group(2))

        # Parse Status information (second part)
        status_pattern = re.compile(
            r'(\d+)\s+'           # ONT ID
            r'(\w+)\s+'           # Run State
            r'([\d-]+\s+[\d:]+)\s+'  # Last UpTime
            r'([\d-]+\s+[\d:]+)\s+'  # Last DownTime
            r'([^\n]+)'           # Last DownCause
            , re.MULTILINE
        )

        # Parse Details information (third part)
        details_pattern = re.compile(
            r'(\d+)\s+'           # ONT ID
            r'(\w+)\s+'           # SN
            r'([^\s]+)\s+'        # Type
            r'(\d+)\s+'           # Distance
            r'([^/]+)/([^\s]+)\s+'  # Rx/Tx power
            r'(.+?)\s*$'          # Description
            , re.MULTILINE
        )

        # Create dictionaries for both parts
        status_info = {}
        for match in status_pattern.finditer(list_output):
            ont_id = match.group(1)
            status_info[ont_id] = {
                'run_state': match.group(2),
                'last_up_time': match.group(3),
                'last_down_time': match.group(4),
                'last_down_cause': match.group(5).strip()
            }

        # Combine information
        for match in details_pattern.finditer(list_output):
            ont_id = match.group(1)
            ont_status = status_info.get(ont_id, {})
            
            ont_info = {
                'frame': frame,
                'slot': slot,
                'port': port,
                'ont_id': ont_id,
                'serial_number': match.group(2),
                'type': match.group(3),
                'distance': f"{match.group(4)}m",
                'optical': {
                    'rx': f"{match.group(5).strip()} dBm",
                    'tx': f"{match.group(6).strip()} dBm"
                },
                'description': match.group(7).strip(),
                'status': {
                    'run_state': ont_status.get('run_state', ''),
                    'last_up_time': ont_status.get('last_up_time', ''),
                    'last_down_time': ont_status.get('last_down_time', ''),
                    'last_down_cause': ont_status.get('last_down_cause', '')
                }
            }
            
            port_info['port_info']['onts'].append(ont_info)

        return port_info

    def close(self) -> None:
        """Close SSH connection."""
        if self.channel:
            self.channel.close()
        self.client.close()
        self.log("Connection closed")

def handle_output(results: Dict) -> None:
    """Format and print the results."""
    def clean_dict(d):
        if isinstance(d, dict):
            return {k: clean_dict(v) for k, v in d.items() 
                   if v not in (None, "", {}, [])}
        elif isinstance(d, list):
            return [clean_dict(i) for i in d if i not in (None, "", {}, [])]
        return d
        
    cleaned_results = clean_dict(results)
    if not cleaned_results:
        cleaned_results = {
            "error": {
                "message": "No ONTs found in this port",
                "type": "NoDataError"
            }
        }
    print(json.dumps(cleaned_results, indent=2, ensure_ascii=False))

def main():
    parser = argparse.ArgumentParser(description='Huawei ONT List Checker')
    parser.add_argument('--host', required=True, help='OLT hostname or IP')
    parser.add_argument('--frame', required=True, help='Frame number')
    parser.add_argument('--slot', required=True, help='Slot number')
    parser.add_argument('--port', required=True, help='Port number')
    parser.add_argument('--username', required=True, help='SSH username')
    parser.add_argument('--password', required=True, help='SSH password')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    checker = ONTListChecker(
        host=args.host,
        username=args.username,
        password=args.password,
        verbose=args.verbose
    )
    
    try:
        checker.connect()
        
        results = checker.check_port_onts(
            frame=args.frame,
            slot=args.slot,
            port=args.port
        )
        
        handle_output(results)
        
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