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
COPY src/ /app/manager/src/
COPY scripts/ /app/manager/scripts/

# Define permissões
RUN chmod -R 755 /app/manager/scripts && \
    chmod -R 755 /app/manager/src && \
    chown -R automation:automation /app/manager

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Configura o Python path
ENV PYTHONPATH=/app/manager/src

# Adiciona os diretórios ao PATH
ENV PATH="/app/manager/scripts:/app/manager/src:${PATH}"

# Expõe a porta SSH
EXPOSE 22

# Copia e configura o entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Define o entrypoint
ENTRYPOINT ["/entrypoint.sh"]