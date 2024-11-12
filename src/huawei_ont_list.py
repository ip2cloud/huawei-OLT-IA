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
            time.sleep(3)
            self.clear_buffer()
            
            self.log(f"Successfully connected to {self.host}")
            self._setup_session()
            
        except Exception as e:
            print(json.dumps({
                "error": {
                    "message": f"Failed to connect to {self.host}: {str(e)}",
                    "type": "ConnectionError"
                }
            }))
            sys.exit(1)

    def clear_buffer(self) -> None:
        """Clear any pending data in the channel buffer."""
        while self.channel.recv_ready():
            self.channel.recv(4096)
            
    def _setup_session(self) -> None:
        """Setup the session with correct configuration mode."""
        commands = [
            'enable',
            'config',
            'undo smart',
            'mmi-mode original-output'
        ]
        
        for cmd in commands:
            self.channel.send(f'{cmd}\n')
            time.sleep(2)
            self.clear_buffer()
        
        self.log("Entered configuration mode")

    def execute_command(self, command: str) -> str:
        """Execute command on the OLT and return output."""
        self.log(f"Executing command: {command}")
        
        self.clear_buffer()
        self.channel.send(f"{command}\n")
        time.sleep(5)
        
        output = ""
        timeout = 30
        start_time = time.time()
        
        while True:
            if time.time() - start_time > timeout:
                break
                
            if self.channel.recv_ready():
                chunk = self.channel.recv(4096).decode('utf-8', errors='ignore')
                output += chunk
                
                if "---- More" in chunk:
                    self.channel.send(' ')
                    time.sleep(2)
                    continue
                
                if ")#" in chunk or ")" in chunk:
                    time.sleep(2)
                    while self.channel.recv_ready():
                        output += self.channel.recv(4096).decode('utf-8', errors='ignore')
                    break
            else:
                time.sleep(0.5)
        
        self.log(f"Command output length: {len(output)}")
        return output

    def check_port_onts(self, frame: str, slot: str, port: str) -> List[Dict]:
        """Check all ONTs in a specific port."""
        try:
            command = f"display ont info summary {frame}/{slot}/{port}"
            output = self.execute_command(command)
            self.log(f"OUTPUT:\n{output}")

            ont_list = []
            
            # Capturando as seções
            status_lines = []
            details_lines = []
            current_section = None
            
            for line in output.split('\n'):
                if 'ONT  Run     Last' in line:
                    current_section = 'status'
                    continue
                elif 'ONT        SN        Type' in line:
                    current_section = 'details'
                    continue
                    
                if current_section == 'status' and re.match(r'^\s*\d+\s+\w+\s+', line):
                    status_lines.append(line)
                elif current_section == 'details' and re.match(r'^\s*\d+\s+[A-F0-9]+\s+', line):
                    details_lines.append(line)

            # Processando status
            status_dict = {}
            status_pattern = re.compile(r'^\s*(\d+)\s+(\w+)\s+([\d-]+\s+[\d:]+)\s+([\d-]+\s+[\d:]+)\s+(.+?)\s*$')
            
            for line in status_lines:
                match = status_pattern.match(line)
                if match:
                    ont_id = match.group(1)
                    status_dict[ont_id] = {
                        'run_state': match.group(2),
                        'last_up_time': match.group(3).strip(),
                        'last_down_time': match.group(4).strip(),
                        'last_down_cause': match.group(5).strip()
                    }

            # Processando detalhes
            details_pattern = re.compile(
                r'^\s*(\d+)\s+'           # ONT ID
                r'([A-F0-9]+)\s+'         # SN
                r'([^\s]+)\s+'            # Type
                r'(\d+|\-)\s+'            # Distance
                r'([^/]+)/([^\s]+)\s+'    # Rx/Tx power
                r'(.+?)\s*$'              # Description
            )

            for line in details_lines:
                match = details_pattern.match(line)
                if match:
                    ont_id = match.group(1)
                    distance = match.group(4)
                    rx_power = match.group(5).strip()
                    tx_power = match.group(6).strip()

                    if distance == '-' or rx_power == '-':
                        distance = '0'
                        rx_power = '0'
                        tx_power = '0'

                    ont_info = {
                        'frame': frame,
                        'slot': slot,
                        'port': port,
                        'ont_id': ont_id,
                        'serial_number': match.group(2),
                        'type': match.group(3),
                        'distance': f"{distance}m",
                        'optical': {
                            'rx': f"{rx_power} dBm",
                            'tx': f"{tx_power} dBm"
                        },
                        'description': match.group(7).strip(),
                        'status': status_dict.get(ont_id, {
                            'run_state': 'unknown',
                            'last_up_time': '',
                            'last_down_time': '',
                            'last_down_cause': ''
                        })
                    }
                    ont_list.append(ont_info)

            return ont_list

        except Exception as e:
            self.log(f"Error processing output: {str(e)}")
            return []

    def close(self) -> None:
        """Close SSH connection."""
        if hasattr(self, 'channel') and self.channel:
            self.channel.close()
        if hasattr(self, 'client') and self.client:
            self.client.close()
        self.log("Connection closed")

def main():
    parser = argparse.ArgumentParser(description='Huawei ONT List Checker')
    parser.add_argument('--host', required=True, help='OLT hostname or IP')
    parser.add_argument('--frame', required=True, help='Frame number')
    parser.add_argument('--slot', required=True, help='Slot number')
    parser.add_argument('--port', required=True, help='Port number')
    parser.add_argument('--username', required=True, help='SSH username')
    parser.add_argument('--password', required=True, help='SSH password')
    parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    # Capture a saída de erro para stderr
    def error_response(message: str, error_type: str = "Error") -> None:
        print(json.dumps({
            "error": {
                "message": message,
                "type": error_type
            }
        }, indent=2))
        sys.exit(1)
    
    args = parser.parse_args()
    checker = None
    
    try:
        checker = ONTListChecker(
            host=args.host,
            username=args.username,
            password=args.password,
            verbose=args.verbose
        )
        
        checker.connect()
        
        results = checker.check_port_onts(
            frame=args.frame,
            slot=args.slot,
            port=args.port
        )
        
        if not results:
            # Se não encontrou resultados, retorna lista vazia mas não erro
            print(json.dumps([], indent=2))
        else:
            # Imprime o JSON formatado no stdout
            print(json.dumps(results, indent=2, ensure_ascii=False))
        
    except paramiko.AuthenticationException:
        error_response("Falha na autenticação. Verifique usuário e senha.", "AuthenticationError")
    except paramiko.SSHException as e:
        error_response(f"Erro de SSH: {str(e)}", "SSHError")
    except Exception as e:
        error_response(str(e), e.__class__.__name__)
    finally:
        if checker:
            try:
                checker.close()
            except:
                pass

if __name__ == '__main__':
    main()