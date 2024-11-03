# Guia de Execução - ONT Manager

## 1. Estrutura do Projeto

Primeiro, crie a estrutura de diretórios:

```bash
mkdir manager
cd manager
mkdir -p src scripts logs ssh_keys
```

## 2. Arquivos Principais

Copie os seguintes arquivos para seus respectivos diretórios:

```plaintext
manager/
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── install.sh                 # instalador
├── huawei-ont-tool          # script wrapper
│
├── src/
│   ├── __init__.py
│   └── huawei_ont_manager.py
│
├── scripts/
│   └── huawei-ont-manager.sh
│
├── logs/
│
└── ssh_keys/
```

## 3. Permissões

Configure as permissões dos scripts:

```bash
chmod +x huawei-ont-tool
chmod +x install.sh
chmod +x scripts/huawei-ont-manager.sh
chmod +x src/huawei_ont_manager.py
```

## 4. Build da Imagem

Você tem várias opções para build:

```bash
# Build padrão (arm64 e amd64)
./install.sh

# Apenas para ARM64
./install.sh --arm64

# Apenas para AMD64
./install.sh --amd64

# Com tag específica
./install.sh --tag 1.0.0

# Para registry
./install.sh --push --registry seu.registry.com
```

## 5. Testar o Acesso

Após o build, teste o acesso SSH:

```bash
ssh -i ssh_keys/automation_key -p 2222 automation@localhost
```

## 6. Uso do Sistema

### Para resetar uma única ONT:

```bash
./huawei-ont-tool reset -o 172.16.0.21 0 2 2 16 user password -v
```

Onde:

- 172.16.0.21 = IP da OLT
- 0 = Frame
- 2 = Slot
- 2 = Porta
- 16 = ONT ID
- user = usuário
- password = senha
- -v = verbose (opcional)

### Para resetar múltiplas ONTs:

```bash
./huawei-ont-tool reset -l 172.16.0.21 0 2 '[{"port":2,"ont":16},{"port":2,"ont":17}]' user password -v
```

## 7. Comandos Úteis

### Verificar status do container:

```bash
docker compose ps
```

### Ver logs do container:

```bash
docker compose logs
```

### Reiniciar o serviço:

```bash
docker compose down
docker compose up -d
```

### Reconstruir após mudanças:

```bash
docker compose down
./install.sh
docker compose up -d
```

## 8. Resolução de Problemas

### Se o SSH não conectar:

```bash
# Verifique os logs
docker compose logs

# Verifique se a porta está aberta
netstat -tuln | grep 2222

# Verifique as permissões das chaves
ls -la ssh_keys/
```

### Se o reset falhar:

```bash
# Use o modo verbose
./huawei-ont-tool reset -o IP FRAME SLOT PORT ONT USER PASS -v

# Verifique os logs em tempo real
tail -f logs/ont_operations_*.log
```

## 9. Backups

Faça backup regular dos arquivos importantes:

```bash
tar -czf ont-manager-backup.tar.gz \
    src/ \
    scripts/ \
    ssh_keys/ \
    Dockerfile \
    docker-compose.yml \
    requirements.txt \
    install.sh \
    install.sh \
    huawei-ont-tool
```

## 10. Atualizações

Para atualizar o sistema:

1. Faça backup dos dados
2. Atualize os arquivos necessários
3. Reconstrua a imagem:

```bash
./install.sh --tag NOVA_VERSAO
```

## 11. Observações Importantes

- Mantenha as chaves SSH seguras
- Faça backup regular dos logs importantes
- Use sempre o modo verbose (-v) ao diagnosticar problemas
- Verifique os logs após cada operação importante
