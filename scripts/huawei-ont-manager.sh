#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

show_help() {
    echo "Huawei ONT Management Tool"
    echo ""
    echo "Uso para ONT única (reset):"
    echo "  $0 reset -o HOST FRAME SLOT PORT ONT USERNAME PASSWORD"
    echo ""
    echo "Uso para lote de ONTs (reset):"
    echo "  $0 reset -l HOST FRAME SLOT ONTS_JSON USERNAME PASSWORD"
    echo ""
    echo "Uso para verificar status (ONT única):"
    echo "  $0 status -o HOST FRAME SLOT PORT_ID ONT USERNAME PASSWORD"
    echo ""
    echo "Uso para verificar status (lote):"
    echo "  $0 status -l HOST ONTS_JSON USERNAME PASSWORD"
}

if [ "$#" -lt 3 ]; then
    print_message "$RED" "Erro: Número insuficiente de argumentos"
    show_help
    exit 1
fi

COMMAND=$1
MODE=$2

case $COMMAND in
    reset)
        if [ "$MODE" == "-o" ]; then
            python3 /app/manager/src/huawei_ont_manager.py --host "$3" --frame "$4" --slot "$5" --port "$6" --ont "$7" --username "$8" --password "$9" --mode single
        elif [ "$MODE" == "-l" ]; then
            python3 /app/manager/src/huawei_ont_manager.py --host "$3" --frame "$4" --slot "$5" --onts "$6" --username "$7" --password "$8" --mode batch
        else
            print_message "$RED" "Modo inválido: use -o para única ONT ou -l para lote"
            show_help
            exit 1
        fi
        ;;
    status)
        if [ "$MODE" == "-o" ]; then
            python3 /app/manager/src/huawei_ont_status_checker.py --host "$3" --frame "$4" --slot "$5" --port_id "$6" --ont "$7" --username "$8" --password "$9" --mode single
        elif [ "$MODE" == "-l" ]; then
            python3 /app/manager/src/huawei_ont_status_checker.py --host "$3" --onts "$4" --username "$5" --password "$6" --mode batch
        else
            print_message "$RED" "Modo inválido: use -o para única ONT ou -l para lote"
            show_help
            exit 1
        fi
        ;;
    *)
        print_message "$RED" "Comando inválido: use reset ou status"
        show_help
        exit 1
        ;;
esac
