#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Variáveis padrão
DEFAULT_IMAGE_NAME="ont-manager"
DEFAULT_IMAGE_TAG="0.1.0"
DEFAULT_PLATFORM="multi"
PUSH_TO_REGISTRY=false
REGISTRY_URL=""
REPOSITORY_NAME=""
VERBOSE=false

# Função para imprimir mensagens com cores
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Função para debug
debug_message() {
    if [ "$VERBOSE" = true ]; then
        print_message "$BLUE" "[DEBUG] $1"
    fi
}

# Função para verificar erros
check_error() {
    if [ $? -ne 0 ]; then
        print_message "$RED" "Erro: $1"
        debug_message "Código de saída: $?"
        debug_message "Último comando executado: $BASH_COMMAND"
        exit 1
    fi
}

# Função para validar configuração
validate_config() {
    debug_message "Validando configuração..."
    
    if [ "$PLATFORM" = "multi" ] && [ "$PUSH_TO_REGISTRY" = false ]; then
        print_message "$RED" "Erro: Build multi-plataforma requer a flag --push"
        debug_message "Build multi-plataforma detectado sem --push"
        print_message "$YELLOW" "Use uma das opções:"
        echo "1. Adicione --push para fazer push para um registry"
        echo "2. Especifique uma plataforma única com -p arm64 ou -p amd64"
        exit 1
    fi
    
    if [ "$PUSH_TO_REGISTRY" = true ] && [ -z "$REGISTRY_URL" ] && [ -z "$REPOSITORY_NAME" ]; then
        print_message "$RED" "Erro: Push requer --registry URL ou --repository REPO"
        debug_message "Push solicitado sem registry ou repository configurado"
        exit 1
    fi
    
    debug_message "Validação concluída com sucesso"
}

# Função para limpar buildx anterior
cleanup_buildx() {
    debug_message "Iniciando limpeza do buildx..."
    print_message "$YELLOW" "Limpando configuração antiga do buildx..."
    
    if docker buildx ls | grep -q multiarch; then
        debug_message "Removendo builder multiarch existente"
        docker buildx rm multiarch 2>/dev/null || true
    fi
    
    debug_message "Executando buildx prune"
    docker buildx prune -f >/dev/null 2>&1 || true
    
    debug_message "Limpeza do buildx concluída"
}

# Função para construir a imagem
build_image() {
    local platforms=""
    case $PLATFORM in
        "arm64")
            platforms="linux/arm64"
            ;;
        "amd64")
            platforms="linux/amd64"
            ;;
        "multi")
            platforms="linux/arm64,linux/amd64"
            ;;
        *)
            print_message "$RED" "Plataforma não suportada: $PLATFORM"
            exit 1
            ;;
    esac

    local build_cmd="docker buildx build --platform $platforms --no-cache"
    local image_name="$IMAGE_NAME"
    
    debug_message "Configuração do build:"
    debug_message "- Plataforma(s): $platforms"
    debug_message "- Nome da imagem: $image_name"
    debug_message "- Tag: $IMAGE_TAG"
    debug_message "- Push ativo: $PUSH_TO_REGISTRY"
    
    if [ "$PUSH_TO_REGISTRY" = true ]; then
        if [ ! -z "$REGISTRY_URL" ]; then
            image_name="$REGISTRY_URL/$image_name"
            debug_message "Registry configurado: $image_name"
        elif [ ! -z "$REPOSITORY_NAME" ]; then
            image_name="$REPOSITORY_NAME/$image_name"
            debug_message "Repository configurado: $image_name"
        fi
        build_cmd="$build_cmd --push"
        debug_message "Build configurado com --push"
    else
        if [ "$PLATFORM" = "multi" ]; then
            debug_message "ERRO: Build multi-plataforma sem push não é suportado"
            exit 1
        else
            build_cmd="$build_cmd --load"
            debug_message "Build configurado com --load para plataforma única"
        fi
    fi

    print_message "$YELLOW" "Construindo imagem para plataforma(s): $platforms"
    debug_message "Comando de build completo:"
    debug_message "$build_cmd -t $image_name:$IMAGE_TAG --builder multiarch ."
    
    if ! $build_cmd -t "$image_name:$IMAGE_TAG" --builder multiarch .; then
        debug_message "Falha no comando de build"
        check_error "Falha no build da imagem"
    fi
    
    debug_message "Build concluído com sucesso"
    if [ "$PUSH_TO_REGISTRY" = false ]; then
        print_message "$GREEN" "Imagem construída localmente com sucesso"
    else
        print_message "$GREEN" "Imagem construída e enviada para o registry com sucesso"
    fi
}

# Função de ajuda
show_help() {
    echo "Uso: $0 [opções]"
    echo
    echo "Opções:"
    echo "  -h, --help                 Mostra esta mensagem de ajuda"
    echo "  -n, --name IMAGE_NAME      Define o nome da imagem (default: $DEFAULT_IMAGE_NAME)"
    echo "  -t, --tag IMAGE_TAG        Define a tag da imagem (default: $DEFAULT_IMAGE_TAG)"
    echo "  -p, --platform PLATFORM    Define a plataforma (arm64|amd64|multi) (default: multi)"
    echo "  -r, --repository REPO      Define o nome do repositório Docker"
    echo "  -v, --verbose             Ativa modo verbose para debugging"
    echo "  --push                     Habilita push para registry"
    echo "  --registry URL             URL do registry para push"
    echo
    echo "Exemplos:"
    echo "  $0 -p arm64               # Build local apenas para ARM64"
    echo "  $0 -p amd64 -t 1.0.0     # Build local para AMD64 com tag específica"
    echo "  $0 -t 1.0.0 --push -r myuser  # Build multi-plataforma com push"
    echo "  $0 -v -p arm64 -t 2.0.0  # Build com modo verbose"
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
        -r|--repository)
            REPOSITORY_NAME="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
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
debug_message "Configurações iniciais:"
debug_message "- Nome da imagem: $IMAGE_NAME"
debug_message "- Tag: $IMAGE_TAG"
debug_message "- Plataforma: $PLATFORM"

# Validar configuração
validate_config

# Para todos os containers e remove imagens antigas
print_message "$YELLOW" "Parando containers existentes e removendo imagens antigas..."
debug_message "Parando containers e removendo imagens..."
docker compose down
docker rmi $(docker images $IMAGE_NAME -q) 2>/dev/null || true
check_error "Falha ao limpar ambiente anterior"

# Configura buildx para multi-arquitetura
print_message "$YELLOW" "Configurando Docker Buildx..."
cleanup_buildx
debug_message "Criando novo builder multiarch..."
docker buildx create --name multiarch --use
debug_message "Inicializando builder..."
docker buildx inspect multiarch --bootstrap
check_error "Falha ao configurar Docker Buildx"

# Executa o build
build_image

# Inicia os containers com a plataforma apropriada
print_message "$YELLOW" "Iniciando novo container..."
debug_message "Executando docker compose up -d"
docker compose build --no-cache && docker compose up -d
check_error "Falha ao iniciar containers"

print_message "$GREEN" "Instalação concluída com sucesso!"