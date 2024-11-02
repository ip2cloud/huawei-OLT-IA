#!/bin/bash
# build.sh

echo "Iniciando build da imagem ONT Manager..."

# Verifica se as chaves SSH existem
if [ ! -f ssh_keys/automation_key.pub ]; then
    echo "Gerando chaves SSH..."
    mkdir -p ssh_keys
    ssh-keygen -t rsa -b 4096 -f ssh_keys/automation_key -N "" -C "automation@ont-manager"
fi

# Garante que os diretórios existem
mkdir -p scripts

# Para os containers existentes
docker compose down

# Remove imagem antiga se existir
docker rmi lideri-ont-manager:latest || true

# Build da nova imagem
docker compose build --no-cache

# Inicia o container
docker compose up -d

echo "Build concluído!"
echo "Para testar o acesso SSH:"
echo "ssh -i ssh_keys/automation_key -p 2222 automation@localhost"