FROM python:3.9-slim

# Define o diretório de trabalho
WORKDIR /app/lideri

# Instala as dependências do sistema incluindo SSH
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libssl-dev \
    openssh-server \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Configura o servidor SSH e cria diretórios necessários
RUN mkdir /var/run/sshd && \
    mkdir -p /app/lideri/logs && \
    mkdir -p /app/lideri/scripts

# Configura o SSH
RUN echo 'PermitRootLogin yes' >> /etc/ssh/sshd_config && \
    echo 'AuthorizedKeysFile .ssh/authorized_keys' >> /etc/ssh/sshd_config

# Gera as host keys do SSH
RUN ssh-keygen -A

# Cria usuário para automação e configura
RUN useradd -m -d /home/automation -s /bin/bash automation && \
    echo "automation:automation" | chpasswd && \
    adduser automation sudo && \
    echo "automation ALL=(ALL) NOPASSWD: ALL" >> /etc/sudoers

# Configura diretório SSH para o usuário automation
RUN mkdir -p /home/automation/.ssh && \
    chown -R automation:automation /home/automation/.ssh && \
    chmod 700 /home/automation/.ssh

# Copia os arquivos do projeto
COPY requirements.txt .
COPY huawei_ont_manager.py .
COPY scripts/huawei-ont-manager.sh /app/lideri/scripts/
COPY ssh_keys/automation_key.pub /home/automation/.ssh/authorized_keys

# Define permissões
RUN chmod 600 /home/automation/.ssh/authorized_keys && \
    chown automation:automation /home/automation/.ssh/authorized_keys && \
    chmod +x huawei_ont_manager.py && \
    chmod +x /app/lideri/scripts/huawei-ont-manager.sh && \
    chown -R automation:automation /app/lideri

# Instala as dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Adiciona o diretório de scripts ao PATH
ENV PATH="/app/lideri/scripts:${PATH}"

# Expõe a porta SSH
EXPOSE 22

# Copia e configura o entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Define o entrypoint
ENTRYPOINT ["/entrypoint.sh"]