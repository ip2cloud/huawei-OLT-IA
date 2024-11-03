import paramiko
import time
import logging
import argparse
import json
from typing import Optional, List, Dict
from datetime import datetime
import os
from pathlib import Path


class HuaweiOLT:
    def __init__(self, host: str, username: str, password: str, port: int = 22, verbose: bool = False):
        """
        Inicializa conexão com OLT Huawei
        """
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.client = None
        self.channel = None
        self.verbose = verbose
        self.logger = self._setup_logger()
        self.current_frame = None
        self.current_slot = None
        self.current_interface = None

    def _setup_logger(self) -> logging.Logger:
        """Configura o logger do sistema com logs em arquivo e console"""
        logger = logging.getLogger('HuaweiOLT')
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
        
        return logger

    def _log_command(self, command: str, output: str, command_type: str = "Comando"):
        """Registra comando e resposta em detalhes"""
        self.logger.debug(f"\n{'-'*50}")
        self.logger.debug(f"{command_type}: {command}")
        self.logger.debug("Resposta:")
        for line in output.splitlines():
            self.logger.debug(f"  {line}")
        self.logger.debug(f"{'-'*50}\n")

    def connect(self) -> bool:
        """Estabelece conexão SSH com a OLT"""
        try:
            self.logger.info(f"Iniciando conexão com OLT {self.host}")
            self.logger.debug(f"Parâmetros de conexão: porta={self.port}, usuário={self.username}")
            
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.logger.debug("Estabelecendo conexão SSH...")
            self.client.connect(
                hostname=self.host,
                username=self.username,
                password=self.password,
                port=self.port
            )
            
            self.logger.debug("Iniciando shell interativo...")
            self.channel = self.client.invoke_shell()
            time.sleep(2)
            
            self._enter_enable_mode()
            self.logger.info(f"Conectado com sucesso à OLT {self.host}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao conectar à OLT: {str(e)}")
            self.logger.debug(f"Detalhes do erro:", exc_info=True)
            return False

    def _enter_enable_mode(self):
        """Entra no modo enable da OLT"""
        self.logger.debug("Entrando no modo enable...")
        enable_output = self.send_command('enable')
        self._log_command('enable', enable_output, "Comando Enable")
        
        time.sleep(1)
        self.logger.debug("Entrando no modo config...")
        config_output = self.send_command('config')
        self._log_command('config', config_output, "Comando Config")

    def send_command(self, command: str, wait_time: int = 2) -> str:
        """
        Envia comando para OLT e retorna resposta
        """
        if not self.channel:
            raise Exception("Não há conexão estabelecida com a OLT")
        
        self.logger.debug(f"Enviando comando: {command}")
        self.channel.send(command + '\n')
        time.sleep(wait_time)
        
        output = ''
        while self.channel.recv_ready():
            chunk = self.channel.recv(4096).decode('utf-8', errors='ignore')
            output += chunk
            if self.verbose:
                self.logger.debug(f"Recebido chunk de dados: {len(chunk)} bytes")
        
        if self.verbose:
            self._log_command(command, output)
            
        return output

    def configure_interface(self, frame_id: int, slot_id: int) -> bool:
        """
        Configura a interface GPON com base no frame e slot
        """
        try:
            self.logger.info(f"Configurando interface GPON {frame_id}/{slot_id}")
            
            # Verifica se já está na interface correta
            if (self.current_frame == frame_id and 
                self.current_slot == slot_id):
                self.logger.debug("Já está na interface correta")
                return True

            # Entra no modo de configuração da interface GPON
            interface_cmd = f'interface gpon {frame_id}/{slot_id}'
            output = self.send_command(interface_cmd)
            
            if self.verbose:
                self._log_command(interface_cmd, output, "Comando Interface")
            
            # Verifica se houve erro
            if 'Error' in output or 'error' in output:
                self.logger.error(f"Erro ao configurar interface GPON {frame_id}/{slot_id}")
                self.logger.error(f"Resposta do comando: {output}")
                return False
            
            # Atualiza estado atual
            self.current_frame = frame_id
            self.current_slot = slot_id
            self.current_interface = f"GPON {frame_id}/{slot_id}"
            
            self.logger.info(f"Interface configurada: {self.current_interface}")
            return True
            
        except Exception as e:
            self.logger.error(f"Erro ao configurar interface: {str(e)}")
            if self.verbose:
                self.logger.debug("Stack trace:", exc_info=True)
            return False

    def reset_multiple_onts(self, ont_list: List[Dict]) -> Dict:
        """
        Reseta múltiplas ONTs em lote
        
        Args:
            ont_list: Lista de dicionários com informações das ONTs
                     [{"port": 1, "ont": 1}, {"port": 1, "ont": 2}, ...]
        
        Returns:
            Dict: Dicionário com resultados do reset de cada ONT
        """
        results = {}
        
        try:
            if not self.current_interface:
                self.logger.error("Interface GPON não configurada")
                return results

            self.logger.info(f"Iniciando reset em lote de {len(ont_list)} ONTs")
            
            for ont_info in ont_list:
                port_id = ont_info['port']
                ont_id = ont_info['ont']
                ont_key = f"{port_id}/{ont_id}"
                
                try:
                    # Comando para resetar a ONT
                    reset_cmd = f'ont reset {port_id} {ont_id}'
                    self.logger.debug(f"Executando comando: {reset_cmd}")
                    
                    # Envia o comando inicial
                    self.channel.send(reset_cmd + '\n')
                    time.sleep(2)  # Aguarda a pergunta de confirmação
                    
                    # Captura a resposta inicial
                    output = ''
                    while self.channel.recv_ready():
                        output += self.channel.recv(4096).decode('utf-8', errors='ignore')
                    
                    # Envia confirmação 'y'
                    if "Are you sure" in output:
                        self.logger.debug(f"Enviando confirmação 'y' para ONT {ont_key}")
                        self.channel.send('y\n')
                        time.sleep(3)  # Aguarda a conclusão do reset
                        
                        # Captura a resposta final
                        while self.channel.recv_ready():
                            output += self.channel.recv(4096).decode('utf-8', errors='ignore')
                    
                    if self.verbose:
                        self._log_command(f"{reset_cmd} (ONT {ont_key})", output, "Comando Reset em Lote")
                    
                    # Verifica se houve erro
                    if 'Error' in output or 'error' in output or 'Command' in output:
                        self.logger.error(f"Erro ao resetar ONT {ont_key}")
                        self.logger.error(f"Resposta: {output}")
                        results[ont_key] = False
                    else:
                        self.logger.info(f"ONT {ont_key} resetada com sucesso")
                        results[ont_key] = True
                    
                    # Pequena pausa entre resets
                    time.sleep(1)
                    
                except Exception as e:
                    self.logger.error(f"Erro ao resetar ONT {ont_key}: {str(e)}")
                    results[ont_key] = False
                    if self.verbose:
                        self.logger.debug("Stack trace:", exc_info=True)
            
            return results
            
        except Exception as e:
            self.logger.error(f"Erro no processo de reset em lote: {str(e)}")
            if self.verbose:
                self.logger.debug("Stack trace:", exc_info=True)
            return results

    def verify_ont_status(self, port_id: int, ont_id: int) -> Optional[str]:
        """
        Verifica o status da ONT após reset
        """
        try:
            self.logger.info(f"Verificando status da ONT {port_id}/{ont_id}")
            
            # Comando para verificar status da ONT
            status_cmd = f'display ont info {port_id} {ont_id}'
            self.logger.debug(f"Executando comando: {status_cmd}")
            
            output = self.send_command(status_cmd)
            
            if self.verbose:
                self._log_command(status_cmd, output, "Comando Status")
            
            # Processa a saída para extrair o status
            status = None
            for line in output.splitlines():
                if 'Run state' in line:
                    status = line.split(':')[-1].strip()
                    self.logger.info(f"Status atual da ONT {port_id}/{ont_id}: {status}")
                    break
            
            if not status and self.verbose:
                self.logger.debug("Status não encontrado na saída")
                self.logger.debug("Saída completa:")
                self.logger.debug(output)
            
            return status
            
        except Exception as e:
            self.logger.error(f"Erro ao verificar status da ONT: {str(e)}")
            if self.verbose:
                self.logger.debug("Stack trace:", exc_info=True)
            return None

    def disconnect(self):
        """Encerra conexão com a OLT"""
        if self.client:
            self.client.close()
            self.logger.info("Conexão encerrada")


def main():
    parser = argparse.ArgumentParser(description='Gerenciador de ONTs Huawei')
    parser.add_argument('--host', required=True, help='Endereço IP da OLT')
    parser.add_argument('--frame', required=True, type=int, help='ID do Frame (Chassi)')
    parser.add_argument('--slot', required=True, type=int, help='ID do Slot')
    parser.add_argument('--port', type=int, help='ID da Porta (usado com --ont)')
    parser.add_argument('--ont', type=int, help='ID da ONT (usado com --port)')
    parser.add_argument('--onts', help='Lista de ONTs em JSON para modo lote')
    parser.add_argument('--username', required=True, help='Usuário para login')
    parser.add_argument('--password', required=True, help='Senha para login')
    parser.add_argument('--verbose', '-v', action='store_true', help='Modo verbose com logs detalhados')
    parser.add_argument('--mode', choices=['single', 'batch'], required=True, help='Modo de operação: single ou batch')
    
    args = parser.parse_args()

    # Inicializa conexão com a OLT
    olt = HuaweiOLT(
        host=args.host,
        username=args.username,
        password=args.password,
        verbose=args.verbose
    )
    
    try:
        # Conecta na OLT
        if not olt.connect():
            return
        
        # Configura interface GPON
        if not olt.configure_interface(args.frame, args.slot):
            return
        
        if args.mode == 'single':
            if not args.port or not args.ont:
                print("Erro: --port e --ont são obrigatórios no modo single")
                return
            
            # Cria lista com uma única ONT
            ont_list = [{"port": args.port, "ont": args.ont}]
        else:  # mode == 'batch'
            if not args.onts:
                print("Erro: --onts é obrigatório no modo batch")
                return
                
            try:
                ont_list = json.loads(args.onts)
            except json.JSONDecodeError:
                print("Erro: O formato da lista de ONTs é inválido. Use o formato JSON correto.")
                return

        # Reseta as ONTs
        results = olt.reset_multiple_onts(ont_list)
        
        # Mostra resultados
        print("\nResultados do reset:")
        print("-" * 40)
        for ont_key, success in results.items():
            status = "Sucesso" if success else "Falha"
            print(f"ONT {ont_key}: {status}")
        print("-" * 40)
        
        # Aguarda e verifica status
        if any(results.values()):
            print("\nAguardando 10 segundos para as ONTs reiniciarem...")
            time.sleep(10)
            
            print("\nStatus final das ONTs:")
            print("-" * 40)
            for ont_info in ont_list:
                if results.get(f"{ont_info['port']}/{ont_info['ont']}", False):
                    status = olt.verify_ont_status(ont_info['port'], ont_info['ont'])
                    print(f"ONT {ont_info['port']}/{ont_info['ont']}: {status or 'Status desconhecido'}")
            print("-" * 40)
            
    finally:
        olt.disconnect()

if __name__ == "__main__":
    main()