#!/bin/bash

# Configura o fuso horário
ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Verifica e cria diretórios necessários
mkdir -p /app/lideri/logs
mkdir -p /var/run/sshd

# Verifica e configura as host keys SSH se necessário
if [ ! -f /etc/ssh/ssh_host_rsa_key ]; then
    ssh-keygen -t rsa -f /etc/ssh/ssh_host_rsa_key -N ''
fi
if [ ! -f /etc/ssh/ssh_host_ecdsa_key ]; then
    ssh-keygen -t ecdsa -f /etc/ssh/ssh_host_ecdsa_key -N ''
fi
if [ ! -f /etc/ssh/ssh_host_ed25519_key ]; then
    ssh-keygen -t ed25519 -f /etc/ssh/ssh_host_ed25519_key -N ''
fi

# Configura permissões dos diretórios
chown -R automation:automation /app/lideri/logs
chmod 755 /app/lideri/logs

# Configura permissões SSH
mkdir -p /home/automation/.ssh
chmod 700 /home/automation/.ssh
chown automation:automation /home/automation/.ssh

if [ -f /home/automation/.ssh/authorized_keys ]; then
    chmod 600 /home/automation/.ssh/authorized_keys
    chown automation:automation /home/automation/.ssh/authorized_keys
fi

# Verifica configurações do SSH
if ! grep -q "PermitRootLogin" /etc/ssh/sshd_config; then
    echo "PermitRootLogin yes" >> /etc/ssh/sshd_config
fi
if ! grep -q "AuthorizedKeysFile" /etc/ssh/sshd_config; then
    echo "AuthorizedKeysFile .ssh/authorized_keys" >> /etc/ssh/sshd_config
fi

# Garante que o PATH inclui os scripts
export PATH="/app/lideri/scripts:${PATH}"

# Verifica permissões dos scripts
chmod +x /app/lideri/scripts/huawei-ont-manager.sh
chmod +x /app/lideri/huawei_ont_manager.py

echo "Iniciando servidor SSH..."
exec /usr/sbin/sshd -D -e  # -e para log no stderr