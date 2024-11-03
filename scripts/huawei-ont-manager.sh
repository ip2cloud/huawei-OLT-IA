#!/bin/bash

# Função para mostrar ajuda
show_help() {
    echo "Huawei ONT Management Tool"
    echo "Uso: $0 COMANDO HOST FRAME SLOT ONTS USERNAME PASSWORD [-v|--verbose]"
    echo ""
    echo "Comandos disponíveis:"
    echo "  reset    - Reseta ONTs específicas"
    echo ""
    echo "Exemplo para uma única ONT:"
    echo "  $0 reset 192.168.1.10 0 1 '[{\"port\":2,\"ont\":16}]' admin senha123 --verbose"
    echo ""
    echo "Exemplo para múltiplas ONTs:"
    echo "  $0 reset 192.168.1.10 0 1 '[{\"port\":2,\"ont\":16},{\"port\":2,\"ont\":17}]' admin senha123 --verbose"
}

# Verifica argumentos
if [ "$#" -lt 7 ]; then
    show_help
    exit 1
fi

# Captura os argumentos
COMMAND=$1
HOST=$2
FRAME=$3
SLOT=$4
ONTS=$5
USERNAME=$6
PASSWORD=$7
VERBOSE=${8:-""}

# Configura o verbose flag
VERBOSE_FLAG=""
if [ "$VERBOSE" == "-v" ] || [ "$VERBOSE" == "--verbose" ]; then
    VERBOSE_FLAG="--verbose"
fi

# Executa o comando apropriado
case $COMMAND in
    "reset")
        python /app/lideri/huawei_ont_manager.py \
            --host "$HOST" \
            --frame "$FRAME" \
            --slot "$SLOT" \
            --onts "$ONTS" \
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