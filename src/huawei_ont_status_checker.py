import paramiko
import time
import logging
import argparse
import json
from typing import List, Optional, Dict
from datetime import datetime
from pathlib import Path

class HuaweiOLTStatusChecker:
    def __init__(self, host: str, username: str, password: str, port: int = 22, verbose: bool = False):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.verbose = verbose
        self.client = None
        self.channel = None
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """Configura o logger do sistema com logs em arquivo e console"""
    logger = logging.getLogger('HuaweiOLTStatusChecker')
    logger.setLevel(logging.DEBUG if self.verbose else logging.INFO)
    
    # Cria diretório de logs se não existir
    log_dir = Path('/app/manager/logs')
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Nome do arquivo de log com data
    log_file = log_dir / f"ont_operations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Handler para arquivo
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)  # Sempre salva logs detalhados no arquivo
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if self.verbose else logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    # Remove handlers existentes
    logger.handlers = []
    
    # Adiciona os novos handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    if self.verbose:
        logger.debug("Modo verbose ativado.")
    
    return logger

    def connect(self) -> bool:
        try:
            self.logger.info(f"Iniciando conexão com OLT {self.host}")
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                hostname=self.host,
                username=self.username,
                password=self.password,
                port=self.port
            )
            self.channel = self.client.invoke_shell()
            time.sleep(2)
            self.logger.info(f"Conectado com sucesso à OLT {self.host}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao conectar à OLT: {str(e)}")
            return False

    def send_command(self, command: str, wait_time: int = 2) -> str:
        if not self.channel:
            raise Exception("Conexão SSH não estabelecida.")
        
        self.logger.debug(f"Enviando comando: {command}")
        self.channel.send(command + '\n')
        time.sleep(wait_time)
        
        output = ''
        while self.channel.recv_ready():
            output += self.channel.recv(4096).decode('utf-8', errors='ignore')
        
        self.logger.debug(f"Resposta do comando: {output}")
        return output

    def verify_ont_status(self, frame_id: int, slot_id: int, port_id: int, ont_id: int) -> Optional[str]:
        try:
            status_cmd = f'display ont info {frame_id} {slot_id} {port_id} {ont_id}'.strip()
            output = self.send_command(status_cmd)
            status = None
            for line in output.splitlines():
                if 'Run state' in line:
                    status = line.split(':')[-1].strip()
                    break
            return status or "Status desconhecido"
        except Exception as e:
            self.logger.error(f"Erro ao verificar status da ONT {frame_id}/{slot_id}/{port_id}/{ont_id}: {str(e)}")
            return None

    def check_status_batch(self, ont_list: List[Dict]) -> Dict[str, str]:
        results = {}
        for ont_info in ont_list:
            frame_id = ont_info['frame']
            slot_id = ont_info['slot']
            port_id = ont_info['port']
            ont_id = ont_info['ont']
            status = self.verify_ont_status(frame_id, slot_id, port_id, ont_id)
            results[f"{frame_id}/{slot_id}/{port_id}/{ont_id}"] = status
        return results

    def disconnect(self):
        if self.client:
            self.client.close()
            self.logger.info("Conexão encerrada")

def main():
    parser = argparse.ArgumentParser(description="Verificador de Status de ONTs Huawei")
    parser.add_argument('--host', required=True, help="Endereço IP da OLT")
    parser.add_argument('--username', required=True, help="Usuário de autenticação")
    parser.add_argument('--password', required=True, help="Senha de autenticação")
    parser.add_argument('--port', default=22, type=int, help="Porta de conexão SSH")
    parser.add_argument('--verbose', '-v', action='store_true', help="Modo verbose")
    parser.add_argument('--mode', choices=['single', 'batch'], required=True, help="Modo de operação")
    parser.add_argument('--ont', type=int, help="ID da ONT (modo single)")
    parser.add_argument('--port_id', type=int, help="ID da porta (modo single)")
    parser.add_argument('--frame', type=int, help="ID do frame (modo single)")
    parser.add_argument('--slot', type=int, help="ID do slot (modo single)")
    parser.add_argument('--onts', help="JSON com lista de ONTs (modo batch)")

    args = parser.parse_args()
    checker = HuaweiOLTStatusChecker(
        host=args.host,
        username=args.username,
        password=args.password,
        port=args.port,
        verbose=args.verbose
    )

    # Exibe os valores dos parâmetros para depuração
    print(f"Modo: {args.mode}")
    print(f"Host: {args.host}")
    print(f"Frame: {args.frame}")
    print(f"Slot: {args.slot}")
    print(f"Port ID: {args.port_id}")
    print(f"ONT ID: {args.ont}")
    print(f"ONTs (batch): {args.onts}")

    if not checker.connect():
        return
    
    try:
        if args.mode == "single":
            # Confere novamente se todos os parâmetros estão presentes no modo single
            if args.frame is None or args.slot is None or args.port_id is None or args.ont is None:
                print("Erro: Parâmetros 'frame', 'slot', 'port_id', e 'ont' são obrigatórios no modo 'single'.")
                return
            status = checker.verify_ont_status(args.frame, args.slot, args.port_id, args.ont)
            print(f"ONT {args.frame}/{args.slot}/{args.port_id}/{args.ont}: {status}")
        elif args.mode == "batch":
            if not args.onts:
                print("Erro: Parâmetro '--onts' é obrigatório no modo 'batch'.")
                return
            ont_list = json.loads(args.onts)
            results = checker.check_status_batch(ont_list)
            for ont_key, status in results.items():
                print(f"ONT {ont_key}: {status}")
        else:
            print("Erro: Modo de operação desconhecido.")
    finally:
        checker.disconnect()

if __name__ == "__main__":
    main()