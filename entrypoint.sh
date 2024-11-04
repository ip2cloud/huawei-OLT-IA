#!/bin/bash

# Configuração de logs
STDOUT_LOG="/app/manager/logs/entrypoint.log"
STDERR_LOG="/app/manager/logs/entrypoint.error.log"

# Criar diretório de logs se não existir
mkdir -p /app/manager/logs

# Redirecionar STDOUT e STDERR para arquivos e console
exec 1> >(tee -a "${STDOUT_LOG}")
exec 2> >(tee -a "${STDERR_LOG}")

# Define timestamp para os logs
log_timestamp() {
    while read -r line; do
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line"
    done
}

# Aplicar timestamp nos logs
exec 1> >(log_timestamp)
exec 2> >(log_timestamp)
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
log $YELLOW "Verificando huawei-ont-manager.sh..."
check_command huawei-ont-manager.sh

# Configuração SSH
log $BLUE "=== Configurando SSH ==="

# Configura diretório SSH do usuário automation
log $YELLOW "Configurando diretório SSH do usuário..."
mkdir -p /home/automation/.ssh
chmod 700 /home/automation/.ssh
chown automation:automation /home/automation/.ssh
check_result "Diretório SSH configurado"

# Gera novo par de chaves se não existir
log $YELLOW "Verificando/Gerando chaves SSH..."
if [ ! -f /home/automation/.ssh/automation_key ]; then
    log $YELLOW "Gerando novo par de chaves SSH..."
    ssh-keygen -t rsa -b 4096 -f /home/automation/.ssh/automation_key -N "" -C "automation@ont-manager"
    check_result "Par de chaves SSH gerado"

    log $BLUE "=== Informações de Acesso SSH ==="
    log $YELLOW "IMPORTANTE: Salve a chave privada abaixo. Ela será exibida apenas uma vez!"
    log $YELLOW "========== INÍCIO DA CHAVE PRIVADA =========="
    cat /home/automation/.ssh/automation_key
    log $YELLOW "========== FIM DA CHAVE PRIVADA ============="
    echo ""
    
    log $YELLOW "Chave pública correspondente:"
    log $GREEN "$(cat /home/automation/.ssh/automation_key.pub)"
    echo ""
    
    # Copia a chave pública para authorized_keys
    cp /home/automation/.ssh/automation_key.pub /home/automation/.ssh/authorized_keys
    chmod 600 /home/automation/.ssh/authorized_keys
    chown automation:automation /home/automation/.ssh/authorized_keys
    
    log $YELLOW "Instruções de uso:"
    log $GREEN "1. Copie a chave privada acima para um arquivo local (ex: automation_key)"
    log $GREEN "2. Execute: chmod 600 automation_key"
    log $GREEN "3. Conecte usando: ssh -i automation_key -p 2222 automation@<ip_do_host>"
    echo ""
    
    # Remove a chave privada por segurança
    #log $YELLOW "Removendo chave privada do container por segurança..."
    #shred -u /home/automation/.ssh/automation_key
    #check_result "Chave privada removida com segurança"
fi

# Verifica e gera as host keys SSH
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

# Configura sshd_config
log $YELLOW "Configurando sshd_config..."
{
    echo "PermitRootLogin no"
    echo "PubkeyAuthentication yes"
    echo "PasswordAuthentication no"
    echo "ChallengeResponseAuthentication no"
    echo "UsePAM yes"
    echo "Subsystem sftp /usr/lib/openssh/sftp-server"
    echo "AuthorizedKeysFile .ssh/authorized_keys"
} > /etc/ssh/sshd_config
check_result "sshd_config configurado"

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

log $GREEN "=== Configuração concluída. Iniciando SSHD... ==="

# Inicia o SSH em modo debug
exec /usr/sbin/sshd -D -e