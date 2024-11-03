#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variáveis padrão
DEFAULT_IMAGE_NAME="ont-manager"
DEFAULT_IMAGE_TAG="0.1.0"
DEFAULT_PLATFORM="linux/arm64,linux/amd64"
PUSH_TO_REGISTRY=false
REGISTRY_URL=""

# Função para imprimir mensagens com cores
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Função para verificar erros
check_error() {
    if [ $? -ne 0 ]; then
        print_message "$RED" "Erro: $1"
        exit 1
    fi
}

# Função para limpar buildx anterior
cleanup_buildx() {
    print_message "$YELLOW" "Limpando configuração antiga do buildx..."
    docker buildx rm multiarch 2>/dev/null || true
    docker buildx prune -f >/dev/null 2>&1 || true
}

# Função para construir a imagem
build_image() {
    local build_cmd="docker buildx build"
    
    if [ "$PUSH_TO_REGISTRY" = true ] && [ ! -z "$REGISTRY_URL" ]; then
        local full_image_name="$REGISTRY_URL/$IMAGE_NAME:$IMAGE_TAG"
        build_cmd="$build_cmd -t $full_image_name --push"
        print_message "$YELLOW" "Construindo e enviando para registry: $full_image_name"
    else
        # Para build local, construímos uma plataforma por vez
        if [[ $PLATFORM == *","* ]]; then
            print_message "$YELLOW" "Building multiple platforms locally..."
            # Para cada plataforma no PLATFORM
            IFS=',' read -ra PLATS <<< "$PLATFORM"
            for plat in "${PLATS[@]}"; do
                print_message "$YELLOW" "Building for $plat"
                $build_cmd --platform "$plat" -t "$IMAGE_NAME:$IMAGE_TAG" --load .
                check_error "Falha no build da imagem para $plat"
            done
            return
        else
            build_cmd="$build_cmd --platform $PLATFORM -t $IMAGE_NAME:$IMAGE_TAG --load"
        fi
    fi

    print_message "$YELLOW" "Plataformas: $PLATFORM"
    $build_cmd .
    check_error "Falha no build da imagem"
}

# Função de ajuda
show_help() {
    echo "Uso: $0 [opções]"
    echo
    echo "Opções:"
    echo "  -h, --help                 Mostra esta mensagem de ajuda"
    echo "  -n, --name IMAGE_NAME      Define o nome da imagem (default: $DEFAULT_IMAGE_NAME)"
    echo "  -t, --tag IMAGE_TAG        Define a tag da imagem (default: $DEFAULT_IMAGE_TAG)"
    echo "  -p, --platform PLATFORM    Define as plataformas para build"
    echo "                             (default: $DEFAULT_PLATFORM)"
    echo "  --amd64                    Compila apenas para linux/amd64"
    echo "  --arm64                    Compila apenas para linux/arm64"
    echo "  --push                     Habilita push para registry"
    echo "  --registry URL             URL do registry para push"
    echo
    echo "Exemplos:"
    echo "  $0 --name minha-imagem --tag 1.0.0 --amd64"
    echo "  $0 --platform 'linux/arm64,linux/amd64' --push --registry docker.io/meuuser"
    echo "  $0 --arm64"
}

# Processar argumentos da linha de comando
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -t|--tag)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -p|--platform)
            PLATFORM="$2"
            shift 2
            ;;
        --amd64)
            PLATFORM="linux/amd64"
            shift
            ;;
        --arm64)
            PLATFORM="linux/arm64"
            shift
            ;;
        --push)
            PUSH_TO_REGISTRY=true
            shift
            ;;
        --registry)
            REGISTRY_URL="$2"
            shift 2
            ;;
        *)
            print_message "$RED" "Opção desconhecida: $1"
            show_help
            exit 1
            ;;
    esac
done

# Configurar valores padrão se não especificados
IMAGE_NAME=${IMAGE_NAME:-$DEFAULT_IMAGE_NAME}
IMAGE_TAG=${IMAGE_TAG:-$DEFAULT_IMAGE_TAG}
PLATFORM=${PLATFORM:-$DEFAULT_PLATFORM}

# Início da execução
print_message "$GREEN" "Iniciando instalação do ONT Manager..."

# Cria estrutura de diretórios
print_message "$YELLOW" "Criando estrutura de diretórios..."
mkdir -p src scripts logs ssh_keys
check_error "Falha ao criar diretórios"

# Cria requirements.txt
print_message "$YELLOW" "Criando arquivo requirements.txt..."
cat > requirements.txt << 'EOF'
paramiko==3.4.0
cryptography==42.0.0
bcrypt==4.1.2
pynacl==1.5.0
EOF
check_error "Falha ao criar requirements.txt"

# Cria __init__.py no diretório src
print_message "$YELLOW" "Criando arquivo __init__.py..."
touch src/__init__.py
check_error "Falha ao criar __init__.py"

# Configura buildx para multi-arquitetura
print_message "$YELLOW" "Configurando Docker Buildx..."
cleanup_buildx
docker buildx create --name multiarch --use
docker buildx inspect multiarch --bootstrap
check_error "Falha ao configurar Docker Buildx"

# Define permissões
print_message "$YELLOW" "Configurando permissões..."
chmod +x huawei-ont-tool
chmod +x install.sh
chmod +x scripts/huawei-ont-manager.sh
chmod +x src/huawei_ont_manager.py
check_error "Falha ao configurar permissões"

# Configura SSH
print_message "$YELLOW" "Configurando SSH..."
if [ ! -f ssh_keys/automation_key ]; then
    print_message "$YELLOW" "Gerando chaves SSH..."
    ssh-keygen -t rsa -b 4096 -f ssh_keys/automation_key -N "" -C "automation@ont-manager"
    cp ssh_keys/automation_key.pub ssh_keys/authorized_keys
fi
check_error "Falha na configuração SSH"

# Executa o build
build_image

# Para os containers existentes e remove
print_message "$YELLOW" "Parando containers existentes..."
docker compose down
check_error "Falha ao parar containers"

# Inicia os novos containers
print_message "$YELLOW" "Iniciando novos containers..."
docker compose up -d
check_error "Falha ao iniciar containers"

print_message "$GREEN" "Instalação concluída com sucesso!"
echo "-----------------------------------"

# Mostra a chave pública
print_message "$YELLOW" "Chave pública SSH gerada:"
echo "-----------------------------------"
cat ssh_keys/automation_key.pub
echo "-----------------------------------"

print_message "$YELLOW" "Instruções de uso:"
print_message "$GREEN" "1. Para ONT única:"
print_message "$GREEN" "docker exec ont-manager huawei-ont-tool reset -o 172.16.0.21 0 2 2 16 lidia lidia2024 -v"
print_message "$GREEN" ""
print_message "$GREEN" "2. Para lote de ONTs:"
print_message "$GREEN" "docker exec ont-manager huawei-ont-tool reset -l 172.16.0.21 0 2 '[{\"port\":2,\"ont\":16},{\"port\":2,\"ont\":17}]' lidia lidia2024 -v"
print_message "$GREEN" ""
print_message "$YELLOW" "Para ver os logs do container:"
print_message "$GREEN" "docker logs -f ont-manager"
print_message "$GREEN" ""
print_message "$YELLOW" "Para entrar no container:"
print_message "$GREEN" "docker exec -it ont-manager bash"
print_message "$GREEN" ""
print_message "$YELLOW" "Status do container:"
docker ps --filter "name=ont-manager" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"