#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Função para imprimir mensagens com cores
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Função para mostrar ajuda
show_help() {
    echo "Huawei ONT Management Tool"
    echo ""
    echo "Uso para ONT única:"
    echo "  $0 reset -o HOST FRAME SLOT PORT ONT USERNAME PASSWORD [-v|--verbose]"
    echo ""
    echo "Uso para lote de ONTs:"
    echo "  $0 reset -l HOST FRAME SLOT ONTS USERNAME PASSWORD [-v|--verbose]"
    echo ""
    echo "Exemplos:"
    echo "  ONT única:"
    echo "  $0 reset -o 192.168.1.10 0 1 2 16 admin senha123 --verbose"
    echo ""
    echo "  Múltiplas ONTs:"
    echo "  $0 reset -l 192.168.1.10 0 1 '[{\"port\":2,\"ont\":16},{\"port\":2,\"ont\":17}]' admin senha123 --verbose"
}

# Verifica número mínimo de argumentos
if [ "$#" -lt 3 ]; then
    print_message "$RED" "Erro: Número insuficiente de argumentos"
    show_help
    exit 1
fi

# Captura o comando e modo
COMMAND=$1
MODE=$2

case $MODE in
    "-o") # Modo única ONT
        if [ "$#" -lt 8 ]; then
            print_message "$RED" "Erro: Argumentos insuficientes para modo única ONT"
            show_help
            exit 1
        fi
        HOST=$3
        FRAME=$4
        SLOT=$5
        PORT=$6
        ONT=$7
        USERNAME=$8
        PASSWORD=$9
        VERBOSE=${10:-""}
        
        print_message "$YELLOW" "Executando reset de ONT única..."
        print_message "$GREEN" "Host: $HOST"
        print_message "$GREEN" "Frame: $FRAME"
        print_message "$GREEN" "Slot: $SLOT"
        print_message "$GREEN" "Port: $PORT"
        print_message "$GREEN" "ONT: $ONT"
        
        VERBOSE_FLAG=""
        if [ "$VERBOSE" == "-v" ] || [ "$VERBOSE" == "--verbose" ]; then
            VERBOSE_FLAG="--verbose"
        fi
        
        python /app/manager/src/huawei_ont_manager.py \
            --mode single \
            --host "$HOST" \
            --frame "$FRAME" \
            --slot "$SLOT" \
            --port "$PORT" \
            --ont "$ONT" \
            --username "$USERNAME" \
            --password "$PASSWORD" \
            $VERBOSE_FLAG
        ;;
        
    "-l") # Modo lote
        if [ "$#" -lt 7 ]; then
            print_message "$RED" "Erro: Argumentos insuficientes para modo lote"
            show_help
            exit 1
        fi
        HOST=$3
        FRAME=$4
        SLOT=$5
        ONTS=$6
        USERNAME=$7
        PASSWORD=$8
        VERBOSE=${9:-""}
        
        print_message "$YELLOW" "Executando reset em lote..."
        print_message "$GREEN" "Host: $HOST"
        print_message "$GREEN" "Frame: $FRAME"
        print_message "$GREEN" "Slot: $SLOT"
        print_message "$GREEN" "ONTs: $ONTS"
        
        VERBOSE_FLAG=""
        if [ "$VERBOSE" == "-v" ] || [ "$VERBOSE" == "--verbose" ]; then
            VERBOSE_FLAG="--verbose"
        fi
        
        python /app/manager/src/huawei_ont_manager.py \
            --mode batch \
            --host "$HOST" \
            --frame "$FRAME" \
            --slot "$SLOT" \
            --onts "$ONTS" \
            --username "$USERNAME" \
            --password "$PASSWORD" \
            $VERBOSE_FLAG
        ;;
        
    *)
        print_message "$RED" "Modo inválido: use -o para única ONT ou -l para lote"
        show_help
        exit 1
        ;;
esac

if [ $? -eq 0 ]; then
    print_message "$GREEN" "Comando executado com sucesso!"
else
    print_message "$RED" "Erro ao executar o comando"
    exit 1
fi