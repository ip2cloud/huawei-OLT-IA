#!/bin/bash

echo "Iniciando instalação do ONT Manager..."

# Cria estrutura de diretórios
mkdir -p scripts logs ssh_keys

# Copia ou cria todos os arquivos necessários
echo "Criando arquivos do projeto..."

# requirements.txt
cat > requirements.txt << 'EOF'
paramiko==3.4.0
cryptography==42.0.0
bcrypt==4.1.2
pynacl==1.5.0
EOF

# Copia os scripts fornecidos anteriormente
# (huawei_ont_manager.py, huawei-ont-manager.sh, etc.)

# Define permissões
chmod +x entrypoint.sh
chmod +x setup_ssh.sh
chmod +x huawei-ont-tool
chmod +x scripts/huawei-ont-manager.sh

# Configura SSH
./setup_ssh.sh

# Constrói e inicia o container
echo "Construindo e iniciando o container..."
docker compose down
docker compose build --no-cache
docker compose up -d

echo "Instalação concluída!"
echo "-----------------------------------"
echo "Para testar a instalação:"
echo "./huawei-ont-tool reset HOST FRAME SLOT PORT ONT USERNAME PASSWORD -v"