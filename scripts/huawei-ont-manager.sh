#!/bin/bash

# Função para mostrar ajuda
show_help() {
    echo "Uso: $0 COMANDO HOST FRAME SLOT PORT ONT USERNAME PASSWORD [-v|--verbose]"
    echo ""
    echo "Comandos disponíveis:"
    echo "  reset    - Reseta uma ONT específica"
    echo ""
    echo "Exemplo:"
    echo "  $0 reset 192.168.1.10 0 1 2 1 admin senha123 --verbose"
    echo ""
    echo "Parâmetros:"
    echo "  HOST      - Endereço IP da OLT"
    echo "  FRAME     - ID do Frame (Chassi)"
    echo "  SLOT      - ID do Slot"
    echo "  PORT      - ID da Porta"
    echo "  ONT       - ID da ONT"
    echo "  USERNAME  - Usuário para login"
    echo "  PASSWORD  - Senha para login"
    echo "  -v, --verbose  - Modo verbose com logs detalhados"
}

# Verifica se há argumentos suficientes
if [ "$#" -lt 8 ]; then
    show_help
    exit 1
fi

# Captura os argumentos
COMMAND=$1
HOST=$2
FRAME=$3
SLOT=$4
PORT=$5
ONT=$6
USERNAME=$7
PASSWORD=$8
VERBOSE=${9:-""}  # Nono argumento opcional

# Cria diretório de logs se não existir
mkdir -p /app/lideri/logs
chmod 777 /app/lideri/logs

# Configura o verbose flag
VERBOSE_FLAG=""
if [ "$VERBOSE" == "-v" ] || [ "$VERBOSE" == "--verbose" ]; then
    VERBOSE_FLAG="--verbose"
fi

# Executa o comando apropriado
case $COMMAND in
    "reset")
        echo "Executando reset com logs em /app/lideri/logs/"
        python /app/lideri/huawei_ont_manager.py \
            --host "$HOST" \
            --frame "$FRAME" \
            --slot "$SLOT" \
            --port "$PORT" \
            --ont "$ONT" \
            --username "$USERNAME" \
            --password "$PASSWORD" \
            $VERBOSE_FLAG
        ;;
    *)
        echo "Comando desconhecido: $COMMAND"
        show_help
        exit 1
        ;;
esac