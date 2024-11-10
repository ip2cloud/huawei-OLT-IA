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
    echo "Comandos disponíveis:"
    echo "  reset        - Reiniciar ONT"
    echo "  status       - Verificar status da ONT"
    echo "  ont-summary  - Listar todas as ONTs de um slot"
    echo ""
    echo "Uso para ONT única:"
    echo "  $0 reset -o HOST FRAME SLOT PORT ONT USERNAME PASSWORD [-v|--verbose]"
    echo "  $0 status -o HOST FRAME SLOT PORT ONT USERNAME PASSWORD [-v|--verbose]"
    echo ""
    echo "Uso para lote de ONTs:"
    echo "  $0 reset -l HOST FRAME SLOT ONTS USERNAME PASSWORD [-v|--verbose]"
    echo "  $0 status -l HOST FRAME SLOT ONTS USERNAME PASSWORD [-v|--verbose]"
    echo ""
    echo "Uso para listar ONTs:"
    echo "  $0 ont-summary HOST FRAME SLOT PORT USERNAME PASSWORD [-v|--verbose]"
    echo ""
    echo "Exemplos:"
    echo "  ONT única:"
    echo "  $0 reset -o 192.168.1.10 0 1 2 16 admin senha123 --verbose"
    echo "  $0 status -o 192.168.1.10 0 1 2 16 admin senha123 --verbose"
    echo ""
    echo "  Múltiplas ONTs:"
    echo "  $0 reset -l 192.168.1.10 0 1 '[{\"port\":2,\"ont\":16},{\"port\":2,\"ont\":17}]' admin senha123 --verbose"
    echo ""
    echo "  Listar ONTs de um slot:"
    echo "  $0 ont-summary 192.168.1.10 0 1 2 admin senha123 --verbose"
}

# Verifica número mínimo de argumentos
if [ "$#" -lt 2 ]; then
    print_message "$RED" "Erro: Número insuficiente de argumentos"
    show_help
    exit 1
fi

# Captura o comando
COMMAND=$1

# Define o script Python baseado no comando
case $COMMAND in
    "reset"|"status")
        if [ "$#" -lt 8 ]; then
            print_message "$RED" "Erro: Argumentos insuficientes para o comando $COMMAND"
            show_help
            exit 1
        fi
        
        MODE=$2
        HOST=$3
        FRAME=$4
        SLOT=$5
        
        if [ "$MODE" == "-o" ]; then
            # Modo única ONT
            if [ "$#" -lt 9 ]; then
                print_message "$RED" "Erro: Argumentos insuficientes para modo única ONT"
                show_help
                exit 1
            fi
            
            PORT=$6
            ONT=$7
            USERNAME=$8
            PASSWORD=$9
            VERBOSE_FLAG=""
            
            # Verifica se existe um argumento verbose
            if [ "${10}" == "-v" ] || [ "${10}" == "--verbose" ]; then
                VERBOSE_FLAG="--verbose"
            fi
            
            print_message "$YELLOW" "Executando $COMMAND de ONT única..."
            print_message "$GREEN" "Host: $HOST"
            print_message "$GREEN" "Frame: $FRAME"
            print_message "$GREEN" "Slot: $SLOT"
            print_message "$GREEN" "Port: $PORT"
            print_message "$GREEN" "ONT: $ONT"
            
            PYTHON_SCRIPT="/app/manager/src/huawei_ont_manager.py"
            
            python "$PYTHON_SCRIPT" \
                --mode single \
                --host "$HOST" \
                --frame "$FRAME" \
                --slot "$SLOT" \
                --port "$PORT" \
                --ont "$ONT" \
                --username "$USERNAME" \
                --password "$PASSWORD" \
                $VERBOSE_FLAG
                
        elif [ "$MODE" == "-l" ]; then
            # Modo lote
            if [ "$#" -lt 8 ]; then
                print_message "$RED" "Erro: Argumentos insuficientes para modo lote"
                show_help
                exit 1
            fi
            
            ONTS=$6
            USERNAME=$7
            PASSWORD=$8
            VERBOSE_FLAG=""
            
            # Verifica se existe um argumento verbose
            if [ "${9}" == "-v" ] || [ "${9}" == "--verbose" ]; then
                VERBOSE_FLAG="--verbose"
            fi
            
            print_message "$YELLOW" "Executando $COMMAND em lote..."
            print_message "$GREEN" "Host: $HOST"
            print_message "$GREEN" "Frame: $FRAME"
            print_message "$GREEN" "Slot: $SLOT"
            print_message "$GREEN" "ONTs: $ONTS"
            
            PYTHON_SCRIPT="/app/manager/src/huawei_ont_manager.py"
            
            python "$PYTHON_SCRIPT" \
                --mode batch \
                --host "$HOST" \
                --frame "$FRAME" \
                --slot "$SLOT" \
                --onts "$ONTS" \
                --username "$USERNAME" \
                --password "$PASSWORD" \
                $VERBOSE_FLAG
        else
            print_message "$RED" "Modo inválido: use -o para única ONT ou -l para lote"
            show_help
            exit 1
        fi
        ;;
        
    "ont-summary")
        if [ "$#" -lt 7 ]; then
            print_message "$RED" "Erro: Argumentos insuficientes para o comando $COMMAND"
            show_help
            exit 1
        fi
        
        HOST=$2
        FRAME=$3
        SLOT=$4
        PORT=$5
        USERNAME=$6
        PASSWORD=$7
        VERBOSE_FLAG=""
        
        if [ "${8}" == "-v" ] || [ "${8}" == "--verbose" ]; then
            VERBOSE_FLAG="--verbose"
        fi
        
        print_message "$YELLOW" "Executando $COMMAND..."
        print_message "$GREEN" "Host: $HOST"
        print_message "$GREEN" "Frame: $FRAME"
        print_message "$GREEN" "Slot: $SLOT"
        print_message "$GREEN" "Port: $PORT"
        
        # Chama o script Python de lista
        python /app/manager/src/huawei_ont_list.py \
            --host "$HOST" \
            --frame "$FRAME" \
            --slot "$SLOT" \
            --port "$PORT" \
            --username "$USERNAME" \
            --password "$PASSWORD" \
            $VERBOSE_FLAG
        ;;
        
    *)
        print_message "$RED" "Comando inválido: use 'reset', 'status' ou 'ont-summary'"
        show_help
        exit 1
        ;;
esac

# Verifica se o comando Python foi bem-sucedido
if [ $? -eq 0 ]; then
    print_message "$GREEN" "Comando executado com sucesso!"
else
    print_message "$RED" "Erro ao executar o comando"
    exit 1
fi