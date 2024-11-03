#!/bin/bash

echo "Configurando ambiente SSH para automação..."

# Cria diretório para chaves SSH se não existir
mkdir -p ssh_keys
chmod 700 ssh_keys

# Gera um novo par de chaves se não existir
if [ ! -f ssh_keys/automation_key ]; then
    echo "Gerando novo par de chaves SSH..."
    ssh-keygen -t rsa -b 4096 -f ssh_keys/automation_key -N "" -C "automation@ont-manager"
    
    # Copia a chave pública para authorized_keys
    cp ssh_keys/automation_key.pub ssh_keys/authorized_keys
fi

# Define permissões corretas
chmod 600 ssh_keys/automation_key
chmod 644 ssh_keys/automation_key.pub ssh_keys/authorized_keys

echo "Configuração SSH concluída!"
echo "-----------------------------------"
echo "Arquivos gerados:"
echo "  - Chave privada: ssh_keys/automation_key"
echo "  - Chave pública: ssh_keys/automation_key.pub"
echo "  - Authorized keys: ssh_keys/authorized_keys"
echo "-----------------------------------"
echo "Para testar após iniciar o container:"
echo "ssh -i ssh_keys/automation_key -p 2222 automation@localhost"