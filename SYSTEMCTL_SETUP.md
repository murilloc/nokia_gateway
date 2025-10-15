# Configuração do Nokia Gateway com Systemctl

Este documento explica como configurar a aplicação Nokia Gateway para ser gerenciada pelo systemctl no Linux, incluindo reinicialização automática em caso de falha.

## Pré-requisitos

- Sistema Linux com systemd
- Aplicação Nokia Gateway instalada e funcionando
- Acesso root ou sudo no sistema
- Python 3.8+ instalado
- Ambiente virtual (venv) configurado com as dependências
- Dependências Python instaladas no venv (requirements.txt)

## Passo 1: Preparação do Ambiente

### 1.1 Verificar ambiente virtual
```bash
# Verificar se o venv existe
ls -la /home/murillo/workspace/nokia_api/venv/

# Verificar o Python do venv
ls -la /home/murillo/workspace/nokia_api/venv/bin/python*
```

### 1.2 Verificar localização da aplicação
```bash
pwd
# Exemplo: /home/murillo/workspace/nokia_api
```

### 1.3 Testar execução manual da aplicação com venv
```bash
cd /home/murillo/workspace/nokia_api
# Ativar o ambiente virtual
source venv/bin/activate
# Testar execução
python nokia_gateway.py
# Desativar ambiente (opcional)
deactivate
```

### 1.4 Verificar dependências no venv
```bash
cd /home/murillo/workspace/nokia_api
source venv/bin/activate
pip list
```

## Passo 2: Considerações Especiais para Virtual Environment

### 2.0 Por que usar script wrapper com venv?

Ao usar um ambiente virtual (venv), **é altamente recomendado** usar um script wrapper pelos seguintes motivos:

1. **Ativação do ambiente**: O venv precisa ser "ativado" antes de executar a aplicação
2. **Isolamento de dependências**: Garantir que as dependências corretas são carregadas
3. **Variáveis de ambiente**: PATH e PYTHONPATH precisam ser configurados corretamente
4. **Facilidade de manutenção**: Mudanças no ambiente podem ser feitas no script sem alterar o systemd
5. **Debugging**: Logs mais claros e verificações de integridade

### Comparação de abordagens:

| Método | Vantagens | Desvantagens |
|--------|-----------|--------------|
| Script Wrapper | Robusto, fácil manutenção, logs claros | Arquivo adicional |
| Execução Direta | Mais simples, menos arquivos | Configuração complexa no systemd |

**RECOMENDAÇÃO**: Use sempre o script wrapper para aplicações em venv.

## Passo 2: Criar Script de Inicialização

### 2.1 Criar script wrapper (OBRIGATÓRIO para venv)
Crie um script que ativa o ambiente virtual e executa a aplicação:

```bash
sudo mkdir -p /opt/nokia_gateway
sudo nano /opt/nokia_gateway/start_gateway.sh
```

Conteúdo do script:
```bash
#!/bin/bash

# Nokia Gateway Startup Script com Virtual Environment
# Configurações
APP_DIR="/home/murillo/workspace/nokia_api"
VENV_DIR="$APP_DIR/venv"
PYTHON_BIN="$VENV_DIR/bin/python"
APP_FILE="nokia_gateway.py"
USER="murillo"

# Função de log
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Iniciando Nokia Gateway..."

# Verificar se o diretório da aplicação existe
if [ ! -d "$APP_DIR" ]; then
    log "ERRO: Diretório da aplicação não encontrado: $APP_DIR"
    exit 1
fi

# Mudar para o diretório da aplicação
cd "$APP_DIR" || {
    log "ERRO: Não foi possível acessar o diretório: $APP_DIR"
    exit 1
}

# Verificar se o ambiente virtual existe
if [ ! -d "$VENV_DIR" ]; then
    log "ERRO: Ambiente virtual não encontrado: $VENV_DIR"
    exit 1
fi

# Verificar se o Python do venv existe
if [ ! -f "$PYTHON_BIN" ]; then
    log "ERRO: Python do venv não encontrado: $PYTHON_BIN"
    exit 1
fi

# Verificar se o arquivo da aplicação existe
if [ ! -f "$APP_FILE" ]; then
    log "ERRO: $APP_FILE não encontrado em $APP_DIR"
    exit 1
fi

# Ativar ambiente virtual (definindo variáveis de ambiente)
export PATH="$VENV_DIR/bin:$PATH"
export VIRTUAL_ENV="$VENV_DIR"
export PYTHONPATH="$APP_DIR"

log "Ambiente virtual ativado: $VENV_DIR"
log "Executando aplicação: $APP_FILE"

# Executar a aplicação usando o Python do venv
exec "$PYTHON_BIN" "$APP_FILE"
```

### 2.2 Tornar o script executável
```bash
sudo chmod +x /opt/nokia_gateway/start_gateway.sh
```

### 2.3 Criar diretório de logs (opcional)
```bash
sudo mkdir -p /var/log/nokia_gateway
sudo chown murillo:murillo /var/log/nokia_gateway
```

## Passo 3: Criar Unit File do Systemd

### 3.1 Criar arquivo de serviço
```bash
sudo nano /etc/systemd/system/nokia-gateway.service
```

### 3.2 Conteúdo do arquivo de serviço (Versão com Virtual Environment)

**Opção A: Usando script wrapper (RECOMENDADO)**
```ini
[Unit]
Description=Nokia Gateway API Service
Documentation=https://github.com/murilloc/nokia_gateway
After=network.target
Wants=network.target

[Service]
# Configurações do processo
Type=simple
User=murillo
Group=murillo
WorkingDirectory=/home/murillo/workspace/nokia_api

# Comando de execução usando script wrapper
ExecStart=/opt/nokia_gateway/start_gateway.sh

# Configurações de reinicialização
Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

# Configurações de segurança
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/murillo/workspace/nokia_api/logs

# Configurações de ambiente para venv
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1

# Configurações de logs
StandardOutput=journal
StandardError=journal
SyslogIdentifier=nokia-gateway

# Configurações de timeout
TimeoutStartSec=30
TimeoutStopSec=30

# Configuração de sinal para parada graceful
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

**Opção B: Execução direta com venv (ALTERNATIVA)**
```ini
[Unit]
Description=Nokia Gateway API Service
Documentation=https://github.com/murilloc/nokia_gateway
After=network.target
Wants=network.target

[Service]
# Configurações do processo
Type=simple
User=murillo
Group=murillo
WorkingDirectory=/home/murillo/workspace/nokia_api

# Comando de execução usando Python do venv diretamente
ExecStart=/home/murillo/workspace/nokia_api/venv/bin/python /home/murillo/workspace/nokia_api/nokia_gateway.py

# Configurações de reinicialização
Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

# Configurações de segurança
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/murillo/workspace/nokia_api/logs

# Configurações de ambiente para venv
Environment=VIRTUAL_ENV=/home/murillo/workspace/nokia_api/venv
Environment=PATH=/home/murillo/workspace/nokia_api/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONPATH=/home/murillo/workspace/nokia_api
Environment=PYTHONUNBUFFERED=1
Environment=PYTHONDONTWRITEBYTECODE=1

# Configurações de logs
StandardOutput=journal
StandardError=journal
SyslogIdentifier=nokia-gateway

# Configurações de timeout
TimeoutStartSec=30
TimeoutStopSec=30

# Configuração de sinal para parada graceful
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
```

**RECOMENDAÇÃO**: Use a **Opção A** com script wrapper, pois é mais robusta e fácil de manter.

## Passo 4: Configurar e Ativar o Serviço

### 4.1 Recarregar configurações do systemd
```bash
sudo systemctl daemon-reload
```

### 4.2 Ativar o serviço para inicialização automática
```bash
sudo systemctl enable nokia-gateway.service
```

### 4.3 Iniciar o serviço
```bash
sudo systemctl start nokia-gateway.service
```

### 4.4 Verificar status do serviço
```bash
sudo systemctl status nokia-gateway.service
```

## Passo 5: Comandos de Gerenciamento

### 5.1 Comandos básicos
```bash
# Iniciar o serviço
sudo systemctl start nokia-gateway.service

# Parar o serviço
sudo systemctl stop nokia-gateway.service

# Reiniciar o serviço
sudo systemctl restart nokia-gateway.service

# Recarregar configuração (se suportado pela aplicação)
sudo systemctl reload nokia-gateway.service

# Ver status detalhado
sudo systemctl status nokia-gateway.service

# Ver logs em tempo real
sudo journalctl -u nokia-gateway.service -f

# Ver logs das últimas 24 horas
sudo journalctl -u nokia-gateway.service --since="24 hours ago"

# Ver logs apenas de hoje
sudo journalctl -u nokia-gateway.service --since today
```

### 5.2 Comandos de habilitação/desabilitação
```bash
# Habilitar inicialização automática
sudo systemctl enable nokia-gateway.service

# Desabilitar inicialização automática
sudo systemctl disable nokia-gateway.service

# Verificar se está habilitado
sudo systemctl is-enabled nokia-gateway.service
```

## Passo 6: Configurações Avançadas de Reinicialização

### 6.1 Política de reinicialização
As configurações no arquivo de serviço garantem:

- **Restart=always**: Reinicia sempre que o processo para (exceto parada manual)
- **RestartSec=10**: Aguarda 10 segundos antes de reiniciar
- **StartLimitInterval=60**: Janela de tempo para contagem de reinicializações
- **StartLimitBurst=3**: Máximo de 3 tentativas de reinicialização em 60 segundos

### 6.2 Modificar política de reinicialização
Para alterar as configurações:

```bash
sudo systemctl edit nokia-gateway.service
```

Adicionar override:
```ini
[Service]
Restart=on-failure
RestartSec=5
StartLimitInterval=120
StartLimitBurst=5
```

## Passo 7: Monitoramento e Logs

### 7.1 Verificar saúde do serviço
```bash
# Status resumido
sudo systemctl is-active nokia-gateway.service

# Status completo
sudo systemctl status nokia-gateway.service --no-pager -l

# Verificar se está habilitado
sudo systemctl is-enabled nokia-gateway.service
```

### 7.2 Monitorar logs
```bash
# Logs em tempo real
sudo journalctl -u nokia-gateway.service -f

# Últimos 100 logs
sudo journalctl -u nokia-gateway.service -n 100

# Logs com timestamps específicos
sudo journalctl -u nokia-gateway.service --since "2025-01-01" --until "2025-01-02"

# Filtrar por prioridade (erro)
sudo journalctl -u nokia-gateway.service -p err
```

### 7.3 Configurar rotação de logs
Criar arquivo de configuração:
```bash
sudo nano /etc/logrotate.d/nokia-gateway
```

Conteúdo:
```
/var/log/nokia_gateway/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    create 644 murillo murillo
    postrotate
        systemctl reload nokia-gateway.service > /dev/null 2>&1 || true
    endscript
}
```

## Passo 8: Verificação e Testes

### 8.1 Testar reinicialização automática
```bash
# Encontrar PID do processo
sudo systemctl show nokia-gateway.service --property=MainPID

# Matar processo para testar reinicialização
sudo kill -9 <PID>

# Verificar se reiniciou automaticamente
sudo systemctl status nokia-gateway.service
```

### 8.2 Testar inicialização automática
```bash
# Reiniciar sistema
sudo reboot

# Após reinicialização, verificar se o serviço iniciou automaticamente
sudo systemctl status nokia-gateway.service
```

### 8.3 Script de verificação de saúde (com verificações de venv)
Criar script de monitoramento:
```bash
sudo nano /opt/nokia_gateway/health_check.sh
```

Conteúdo:
```bash
#!/bin/bash

# Configurações
SERVICE_NAME="nokia-gateway.service"
HEALTH_URL="http://localhost:6778/health"
APP_DIR="/home/murillo/workspace/nokia_api"
VENV_DIR="$APP_DIR/venv"

# Função de log
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S'): $1"
}

# Verificar se o serviço está ativo
if ! systemctl is-active --quiet $SERVICE_NAME; then
    log "ERRO: Serviço $SERVICE_NAME não está ativo"
    exit 1
fi

# Verificar se o ambiente virtual existe
if [ ! -d "$VENV_DIR" ]; then
    log "ERRO: Ambiente virtual não encontrado: $VENV_DIR"
    exit 1
fi

# Verificar se o Python do venv existe
if [ ! -f "$VENV_DIR/bin/python" ]; then
    log "ERRO: Python do venv não encontrado: $VENV_DIR/bin/python"
    exit 1
fi

# Verificar processo em execução
if ! pgrep -f "nokia_gateway.py" > /dev/null; then
    log "AVISO: Processo nokia_gateway.py não encontrado"
fi

# Verificar endpoint de saúde
if ! curl -f -s $HEALTH_URL > /dev/null; then
    log "ERRO: Endpoint de saúde não responde ($HEALTH_URL)"
    exit 1
fi

# Verificar resposta detalhada do endpoint
HEALTH_RESPONSE=$(curl -s $HEALTH_URL)
if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    log "OK: Serviço $SERVICE_NAME está saudável"
    exit 0
else
    log "ERRO: Resposta de saúde inválida: $HEALTH_RESPONSE"
    exit 1
fi
```

### 8.4 Configurar cron para verificação periódica
```bash
sudo crontab -e
```

Adicionar linha:
```
*/5 * * * * /opt/nokia_gateway/health_check.sh >> /var/log/nokia_gateway/health.log 2>&1
```

## Passo 9: Troubleshooting

### 9.1 Problemas comuns e soluções

**Serviço não inicia:**
```bash
# Verificar logs detalhados
sudo journalctl -u nokia-gateway.service --no-pager -l

# Verificar sintaxe do arquivo de serviço
sudo systemd-analyze verify /etc/systemd/system/nokia-gateway.service

# Testar execução manual
cd /home/murillo/workspace/nokia_api
python3 nokia_gateway.py
```

**Permissões negadas:**
```bash
# Verificar propriedade dos arquivos
ls -la /home/murillo/workspace/nokia_api/

# Corrigir permissões se necessário
sudo chown -R murillo:murillo /home/murillo/workspace/nokia_api/
```

**Dependências não encontradas (venv):**
```bash
# Ativar ambiente virtual e instalar dependências
cd /home/murillo/workspace/nokia_api
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

**Problemas com ambiente virtual:**
```bash
# Verificar se o venv está correto
ls -la /home/murillo/workspace/nokia_api/venv/bin/

# Recriar ambiente virtual se necessário
cd /home/murillo/workspace/nokia_api
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Testar script wrapper
sudo /opt/nokia_gateway/start_gateway.sh

# Verificar permissões do venv
sudo chown -R murillo:murillo /home/murillo/workspace/nokia_api/venv/
```

### 9.2 Debug avançado
```bash
# Executar em modo debug
sudo systemctl start nokia-gateway.service
sudo journalctl -u nokia-gateway.service -f

# Verificar variáveis de ambiente
sudo systemctl show nokia-gateway.service --property=Environment

# Analisar tempo de inicialização
sudo systemd-analyze blame | grep nokia-gateway
```

## Passo 10: Backup e Manutenção

### 10.1 Backup da configuração
```bash
# Backup do arquivo de serviço
sudo cp /etc/systemd/system/nokia-gateway.service /etc/systemd/system/nokia-gateway.service.backup

# Backup dos scripts
sudo tar -czf /opt/nokia_gateway_backup_$(date +%Y%m%d).tar.gz /opt/nokia_gateway/
```

### 10.2 Atualização da aplicação (com venv)
```bash
# Parar serviço
sudo systemctl stop nokia-gateway.service

# Atualizar código
cd /home/murillo/workspace/nokia_api
git pull origin main

# Ativar venv e atualizar dependências
source venv/bin/activate
pip install --upgrade -r requirements.txt
deactivate

# Testar aplicação manualmente
source venv/bin/activate
python nokia_gateway.py &
sleep 5
curl http://localhost:6778/health
kill %1  # Matar processo de teste
deactivate

# Reiniciar serviço
sudo systemctl start nokia-gateway.service

# Verificar status
sudo systemctl status nokia-gateway.service
```

## Resumo dos Arquivos Criados

1. **Arquivo de serviço**: `/etc/systemd/system/nokia-gateway.service`
2. **Script de inicialização** (opcional): `/opt/nokia_gateway/start_gateway.sh`
3. **Script de verificação**: `/opt/nokia_gateway/health_check.sh`
4. **Configuração de logrotate**: `/etc/logrotate.d/nokia-gateway`

## Verificação Final - Ambiente Virtual

Para verificar se tudo está funcionando corretamente com o venv:

```bash
# 1. Verificar se o venv está correto
ls -la /home/murillo/workspace/nokia_api/venv/bin/python*

# 2. Testar script wrapper manualmente
sudo -u murillo /opt/nokia_gateway/start_gateway.sh &
sleep 5
curl http://localhost:6778/health
sudo pkill -f nokia_gateway.py

# 3. Verificar status do serviço
sudo systemctl status nokia-gateway.service

# 4. Testar endpoint
curl http://localhost:6778/health

# 5. Verificar logs (procurar por mensagens do venv)
sudo journalctl -u nokia-gateway.service --since "1 hour ago" | grep -i venv

# 6. Verificar se está habilitado para inicialização automática
sudo systemctl is-enabled nokia-gateway.service

# 7. Verificar processo em execução
ps aux | grep nokia_gateway.py

# 8. Testar script de verificação de saúde
sudo /opt/nokia_gateway/health_check.sh
```

## Checklist Final - Virtual Environment

- [ ] ✅ Ambiente virtual existe e está funcional
- [ ] ✅ Script wrapper criado e executável
- [ ] ✅ Arquivo de serviço systemd configurado (Opção A recomendada)
- [ ] ✅ Serviço habilitado para inicialização automática
- [ ] ✅ Serviço iniciado e rodando
- [ ] ✅ Endpoint `/health` respondendo
- [ ] ✅ Logs do systemd funcionando
- [ ] ✅ Script de verificação de saúde funcionando
- [ ] ✅ Teste de reinicialização automática realizado

Com essa configuração, a aplicação Nokia Gateway será:
- Iniciada automaticamente no boot do sistema
- Reiniciada automaticamente em caso de falha
- Gerenciada através de comandos systemctl padrão
- Monitorada através de logs centralizados do systemd
- Protegida por configurações de segurança do systemd
