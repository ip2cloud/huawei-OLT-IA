#!/bin/bash

set -e  # Sai em caso de erro
exec 2>&1  # Redireciona stderr para stdout para capturar todos os logs

# Cores para os logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Função para log
log() {
    local color=$1
    local message=$2
    echo -e "${color}[$(date +%Y-%m-%d\ %H:%M:%S)] ${message}${NC}"
}

# Função para tratamento de erros
handle_error() {
    log $RED "ERROR: $1"
    exit 1
}

# Função para verificar resultado do último comando
check_result() {
    if [ $? -eq 0 ]; then
        log $GREEN "✓ $1"
    else
        handle_error "✗ $1"
    fi
}

# Função para verificar comandos disponíveis
check_command() {
    local cmd=$1
    if command -v $cmd &> /dev/null; then
        log $GREEN "✓ Comando $cmd disponível: $(which $cmd)"
        if [ -x "$(which $cmd)" ]; then
            log $GREEN "✓ Comando $cmd tem permissão de execução"
        else
            log $RED "✗ Comando $cmd não tem permissão de execução"
        fi
    else
        log $RED "✗ Comando $cmd não encontrado"
    fi
}

# Função para mostrar status do container
show_status() {
    log $BLUE "=================== Status do Container ==================="
    log $GREEN "Hostname: $(hostname)"
    log $GREEN "Sistema: $(uname -a)"
    
    log $YELLOW "Diretórios:"
    ls -la /app/manager/
    
    log $YELLOW "Processos em Execução:"
    ps aux
    
    log $YELLOW "Portas em Uso:"
    netstat -tulpn
    
    log $YELLOW "Usuários Logados:"
    who
    
    log $YELLOW "Uso de Memória:"
    free -h
    
    log $YELLOW "Uso de Disco:"
    df -h
    
    log $BLUE "======================================================"
}

log $YELLOW "=== Iniciando configuração do container ONT Manager ==="

# Informações do sistema
log $BLUE "=== Informações do Sistema ==="
log $GREEN "Sistema: $(uname -a)"
log $GREEN "Diretório atual: $(pwd)"
log $GREEN "Usuário: $(whoami)"
log $GREEN "Groups: $(groups)"
log $GREEN "ID: $(id)"

# Configura o fuso horário
log $YELLOW "Configurando timezone para: $TZ"
ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
check_result "Timezone configurado"

# Verifica e cria diretórios necessários
log $YELLOW "Criando diretórios necessários..."
mkdir -p /app/manager/logs
check_result "Diretório de logs criado"
mkdir -p /var/run/sshd
check_result "Diretório SSHD criado"

# Verifica diretórios e permissões
log $BLUE "=== Verificando Estrutura de Diretórios ==="
for dir in /app/manager/logs /app/manager/scripts /app/manager/src /var/run/sshd; do
    if [ -d "$dir" ]; then
        log $GREEN "✓ Diretório $dir existe"
        log $GREEN "  Permissões: $(ls -ld $dir)"
    else
        log $RED "✗ Diretório $dir não encontrado"
    fi
done

log $BLUE "=== Verificando Arquivos Importantes ==="
log $GREEN "Conteúdo de /app/manager:"
ls -la /app/manager/

# Verifica huawei-ont-tool
log $YELLOW "Verificando huawei-ont-tool..."
check_command huawei-ont-tool
if [ -f "/app/manager/huawei-ont-tool" ]; then
    log $GREEN "Permissões do huawei-ont-tool: $(ls -l /app/manager/huawei-ont-tool)"
fi
if [ -L "/usr/local/bin/huawei-ont-tool" ]; then
    log $GREEN "Link simbólico existe: $(ls -l /usr/local/bin/huawei-ont-tool)"
fi

log $YELLOW "Verificando e configurando chaves SSH..."
# Verifica e configura as host keys SSH
for key_type in rsa ecdsa ed25519; do
    key_file="/etc/ssh/ssh_host_${key_type}_key"
    if [ ! -f "$key_file" ]; then
        log $YELLOW "Gerando chave $key_type..."
        ssh-keygen -t $key_type -f $key_file -N ''
        check_result "Chave $key_type gerada"
    else
        log $GREEN "✓ Chave $key_type já existe"
    fi
done

log $YELLOW "Configurando permissões..."
# Configura permissões dos diretórios
chown -R automation:automation /app/manager/logs
chmod 755 /app/manager/logs
check_result "Permissões de logs configuradas"

# Configura permissões SSH
mkdir -p /home/automation/.ssh
chmod 700 /home/automation/.ssh
chown automation:automation /home/automation/.ssh
check_result "Diretório SSH configurado"

if [ -f /home/automation/.ssh/authorized_keys ]; then
    chmod 600 /home/automation/.ssh/authorized_keys
    chown automation:automation /home/automation/.ssh/authorized_keys
    check_result "Arquivo authorized_keys configurado"
fi

log $YELLOW "Configurando SSHD..."
# Verifica configurações do SSH
if ! grep -q "PermitRootLogin" /etc/ssh/sshd_config; then
    echo "PermitRootLogin yes" >> /etc/ssh/sshd_config
    check_result "PermitRootLogin configurado"
fi
if ! grep -q "AuthorizedKeysFile" /etc/ssh/sshd_config; then
    echo "AuthorizedKeysFile .ssh/authorized_keys" >> /etc/ssh/sshd_config
    check_result "AuthorizedKeysFile configurado"
fi

# Verifica configuração do SSHD
log $YELLOW "Verificando configuração do SSHD..."
/usr/sbin/sshd -t
check_result "Configuração do SSHD válida"

# Verifica ambiente Python
log $BLUE "=== Ambiente Python ==="
log $GREEN "Versão Python: $(python --version)"
log $GREEN "Localização Python: $(which python)"
log $GREEN "PYTHONPATH: $PYTHONPATH"
log $GREEN "PATH: $PATH"

# Verifica disponibilidade de scripts
log $BLUE "=== Scripts Disponíveis ==="
check_command python
check_command huawei-ont-manager.sh

log $BLUE "=== Status Final do Container ==="
show_status

log $BLUE "=== Chave SSH para Conexão Remota ==="
if [ -f /home/automation/.ssh/authorized_keys ]; then
    log $YELLOW "Chave pública autorizada para conexão:"
    log $GREEN "$(cat /home/automation/.ssh/authorized_keys)"
    log $YELLOW "Use esta chave para se conectar remotamente via:"
    log $GREEN "ssh -i <sua_chave_privada> -p 2222 automation@<ip_do_host>"
else
    log $RED "Arquivo de chave pública não encontrado!"
fi

log $BLUE "======================================================"

log $GREEN "=== Configuração concluída. Iniciando SSHD... ==="

# Inicia o SSH em modo debug
exec /usr/sbin/sshd -D -e