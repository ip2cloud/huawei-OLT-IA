FROM python:3.9-slim

# Define o diretório de trabalho
WORKDIR /app/manager

# Instala as dependências do sistema incluindo SSH
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libssl-dev \
    openssh-server \
    sudo \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Configura o servidor SSH e cria diretórios necessários
RUN mkdir -p /var/run/sshd \
    /app/manager/logs \
    /app/manager/scripts \
    /app/manager/src

# Cria usuário para automação
RUN useradd -m -d /home/automation -s /bin/bash automation && \
    echo "automation:automation" | chpasswd && \
    adduser automation sudo && \
    echo "automation ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Copia os arquivos do projeto
COPY requirements.txt .
COPY huawei-ont-tool .
COPY src/ /app/manager/src/
COPY scripts/ /app/manager/scripts/
COPY ssh_keys/automation_key.pub /home/automation/.ssh/authorized_keys

# Define permissões
RUN chmod -R 755 /app/manager/scripts && \
    chmod -R 755 /app/manager/src && \
    chmod 755 /app/manager/huawei-ont-tool && \  
    chmod 700 /home/automation/.ssh && \
    chmod 600 /home/automation/.ssh/authorized_keys && \
    chown -R automation:automation /home/automation/.ssh && \
    chown -R automation:automation /app/manager && \
    ln -s /app/manager/huawei-ont-tool /usr/local/bin/huawei-ont-tool  # Link simbólico para acesso global

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Configura o Python path
ENV PYTHONPATH=/app/manager/src

# Adiciona os diretórios ao PATH
ENV PATH="/app/manager:/app/manager/scripts:/app/manager/src:${PATH}"

# Expõe a porta SSH
EXPOSE 22

# Copia e configura o entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Define o entrypoint
ENTRYPOINT ["/entrypoint.sh"]