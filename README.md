# Nokia Gateway API

API Gateway FastAPI para gerenciamento de rede Nokia com autenticação automática de tokens, captura de alarmes/falhas via Kafka e exportação de eventos.

## Características

- ✅ FastAPI REST Gateway na porta 6778
- ✅ Gerenciamento automático de tokens OAuth com refresh a cada 50 minutos
- ✅ Proxy para endpoints da API Nokia
- ✅ Captura de alarmes/falhas em tempo real via Kafka
- ✅ Exportação de eventos para arquivo JSONL
- ✅ Sistema de logging rotacional (10MB por arquivo, 10 backups)
- ✅ Autenticação SSL/TLS com certificados cliente
- ✅ Shutdown gracioso via REST API
- ✅ Execução em background de todos os serviços

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    Nokia Gateway API                         │
│                      (FastAPI - Port 6778)                   │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │  Token Manager   │  │  Alarm Manager   │                │
│  │  (Background)    │  │  (Background)    │                │
│  │  Auto-refresh    │  │  Subscription    │                │
│  │  every 50 min    │  │  renewal 30 min  │                │
│  └──────────────────┘  └──────────────────┘                │
│           │                      │                           │
│           │                      │                           │
│           ▼                      ▼                           │
│  ┌──────────────────────────────────────────┐              │
│  │        Nokia API (10.73.0.181)           │              │
│  │     OAuth Token + Subscription API       │              │
│  └──────────────────────────────────────────┘              │
│                                                               │
│           ┌──────────────────┐                              │
│           │ Kafka Consumer   │                              │
│           │ (Background)     │                              │
│           │ SSL/TLS Auth     │                              │
│           └──────────────────┘                              │
│                    │                                         │
│                    ▼                                         │
│           ┌──────────────────┐                              │
│           │  JSONL Handler   │                              │
│           │  Event Export    │                              │
│           └──────────────────┘                              │
│                    │                                         │
│                    ▼                                         │
│    logs/kafka_messages.jsonl (1 JSON per line)             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Requisitos

- Python 3.8+
- Virtual environment
- Certificados SSL para Kafka (ca.crt, nfmt.pem, key.pem)
- Acesso à API Nokia (10.73.0.181)
- Acesso ao Kafka Broker (10.73.0.181:9193)

## Instalação

### 1. Ativar o Virtual Environment

```bash
# No Linux/Mac
source venv/bin/activate

# No Windows
venv\Scripts\activate
```

### 2. Instalar Dependências

```bash
pip install -r requirements.txt
```

Dependências instaladas:
- `requests==2.31.0` - Cliente HTTP
- `python-dotenv==1.0.0` - Gerenciamento de variáveis de ambiente
- `urllib3==2.1.0` - SSL/TLS
- `fastapi==0.119.0` - Framework REST API
- `uvicorn==0.37.0` - Servidor ASGI
- `kafka-python==2.2.15` - Cliente Kafka

### 3. Configurar Certificados

Coloque os certificados SSL na pasta `certs/`:
```
certs/
├── ca.crt         # CA certificate
├── nfmt.pem       # Client certificate
└── key.pem        # Private key
```

### 4. Configurar Variáveis de Ambiente

Edite o arquivo `.env`:

```bash
# Nokia API Configuration
API_BASE_URL=https://10.73.0.181/rest-gateway/rest/api/v1
API_USERNAME=n6014936
API_PASSWORD=LeoHelo!@345
TOKEN_REFRESH_INTERVAL=3000

# Logging Configuration
LOG_DIR=logs
LOG_LEVEL=INFO
LOG_MAX_BYTES=10485760      # 10MB
LOG_BACKUP_COUNT=10

# Kafka Messages Export
KAFKA_MESSAGES_FILE=logs/kafka_messages.jsonl

# Kafka SSL Certificates
CA=certs/ca.crt
KEY=certs/key.pem
PEM_CERT=certs/nfmt.pem
PASSPHRASE=NokiaNfmt1!
```

## Uso

### Iniciar o Gateway

```bash
# Ativar virtual environment
source venv/bin/activate

# Executar o gateway
python nokia_gateway.py
```

O gateway iniciará na porta **6778** e executará automaticamente:
1. Inicialização do Token Manager (refresh automático a cada 50 min)
2. Criação de subscrição de alarmes na API Nokia
3. Inicialização do Kafka Consumer (SSL/TLS)
4. Background thread para renovação de subscrição (a cada 30 min)

### Logs de Inicialização

```
================================================================================
NOKIA GATEWAY API - STARTING
================================================================================
INFO: Token Manager initialized
INFO: Attempting to get initial access token...
INFO: ✓ Initial token obtained successfully
INFO: Token expiry: 2025-10-15 14:37:15
INFO: Starting automatic token refresh...
INFO: ✓ Auto-refresh started (refresh interval: 3000 seconds)
INFO: Initializing alarm manager...
INFO: Creating subscription for alarms...
INFO: ✓ Subscription created successfully
INFO:   Subscription ID: 0800027ef9f47b48
INFO:   Topic ID: nsp.notification.0800027ef9f47b48
INFO: Creating Kafka consumer for topic: nsp.notification.0800027ef9f47b48
INFO: ✓ Kafka consumer created successfully
INFO: ✓ Started consuming from topic: nsp.notification.0800027ef9f47b48
================================================================================
✓ Nokia Gateway API started successfully
Server ready to accept requests on port 6778
================================================================================
```

## API Endpoints

### 1. Root Endpoint

```http
GET /
```

Retorna informações básicas do serviço.

**Resposta:**
```json
{
  "service": "Nokia Gateway API",
  "version": "1.0.0",
  "status": "running"
}
```

### 2. Health Check

```http
GET /health
```

Verifica o status do serviço e validade do token.

**Resposta:**
```json
{
  "status": "healthy",
  "service": "Nokia Gateway API",
  "token_valid": true
}
```

### 3. Trail List

```http
GET /api/v1/nokia_gateway/trail_list?network_id={network_id}
```

Obtém a lista de trails para um network ID específico.

**Parâmetros:**
- `network_id` (query, required): Network ID (ex: '788602')

**Exemplo:**
```bash
curl "http://localhost:6778/api/v1/nokia_gateway/trail_list?network_id=788602"
```

**Resposta:** Array de objetos com informações de trails
```json
[
  {
    "id": "trail_id_1",
    "name": "Trail Name",
    "status": "active",
    ...
  }
]
```

**Códigos de Status:**
- `200` - Sucesso
- `401` - Falha de autenticação
- `404` - Network ID não encontrado
- `502` - Erro no servidor Nokia API
- `503` - Serviço de autenticação indisponível
- `504` - Timeout na requisição (30s)

### 4. Alarm Status

```http
GET /api/v1/nokia_gateway/alarm_status
```

Obtém o status do alarm manager incluindo informações de subscrição e Kafka consumer.

**Resposta:**
```json
{
  "status": "success",
  "data": {
    "subscription_id": "0800027ef9f47b48",
    "topic_id": "nsp.notification.0800027ef9f47b48",
    "kafka_consuming": true,
    "renewal_active": true
  }
}
```

### 5. Shutdown

```http
POST /shutdown
```

Para o Nokia Gateway API graciosamente.

**Resposta:**
```json
{
  "status": "success",
  "message": "Nokia Gateway API is shutting down...",
  "note": "All services will be stopped gracefully"
}
```

**Exemplo:**
```bash
curl -X POST http://localhost:6778/shutdown
```

## Sistema de Alarmes/Falhas

### Subscrição Automática

O gateway cria automaticamente uma subscrição para a categoria **NSP-FAULT** com os seguintes parâmetros:

```json
{
  "category": "NSP-FAULT",
  "propertyFilter": "severity = 'warning'",
  "scope": "All"
}
```

### Kafka Consumer

O consumer Kafka conecta-se automaticamente ao tópico da subscrição usando:
- **Protocolo:** SSL/TLS
- **Autenticação:** Certificados cliente (nfmt.pem + key.pem)
- **CA Certificate:** ca.crt
- **Group ID:** nokia-gateway-group
- **Auto offset reset:** earliest
- **Auto commit:** Habilitado

### Eventos Capturados

Quando um alarme/falha é recebido:
1. **Console:** Mensagem formatada exibida no terminal
2. **JSONL:** Evento exportado para `logs/kafka_messages.jsonl`
3. **Logs:** Evento registrado em `logs/application.log`

**Exemplo de saída no console:**
```
================================================================================
NEW ALARM/FAULT EVENT
================================================================================
{
  "eventType": "ALARM",
  "severity": "warning",
  "objectFullName": "/nsp/network/element/...",
  "probableCause": "...",
  "specificProblem": "...",
  ...
}
================================================================================
```

### Exportação JSONL

Cada evento Kafka é salvo em `logs/kafka_messages.jsonl` no formato:

```json
{"timestamp": "2025-10-15T13:45:32.123456Z", "received_at": "2025-10-15T10:45:32.123456", "message": {...}}
{"timestamp": "2025-10-15T13:46:15.789012Z", "received_at": "2025-10-15T10:46:15.789012", "message": {...}}
```

Cada linha é um objeto JSON completo contendo:
- `timestamp`: UTC timestamp (ISO 8601)
- `received_at`: Local timestamp (ISO 8601)
- `message`: Conteúdo completo da mensagem Kafka

### Renovação Automática

A subscrição é renovada automaticamente a cada **30 minutos** em background thread para garantir que não expire.

## Sistema de Logging

### Configuração

O sistema de logging usa `RotatingFileHandler` com:
- **Tamanho máximo por arquivo:** 10MB
- **Número de backups:** 10 arquivos
- **Diretório:** `logs/`
- **Nível de log:** INFO (configurável via .env)

### Arquivos de Log

```
logs/
├── application.log       # Log principal (INFO+)
├── application.log.1     # Backup 1
├── application.log.2     # Backup 2
├── ...
├── application.log.10    # Backup 10
├── error.log            # Apenas erros (ERROR+)
└── kafka_messages.jsonl # Eventos Kafka exportados
```

### Formato de Log

```
2025-10-15 10:37:15 - token_manager - INFO - ✓ Token refreshed successfully
2025-10-15 10:42:33 - kafka_consumer - INFO - ✓ Message #1 received from Kafka
2025-10-15 11:07:15 - alarm_subscription - INFO - ✓ Subscription renewed successfully
```

## Shutdown da Aplicação

### Método 1: Ctrl+C (CLI)

Pressione `Ctrl+C` no terminal para parar graciosamente:

```bash
^C
================================================================================
NOKIA GATEWAY API - SHUTTING DOWN
================================================================================
INFO: Stopping alarm manager...
INFO: Stopping Kafka consumer...
INFO: Kafka consumer closed
INFO: ✓ Kafka consumer thread stopped successfully
INFO: ✓ Nokia Gateway API stopped gracefully
================================================================================
```

### Método 2: REST API

```bash
curl -X POST http://localhost:6778/shutdown
```

### Método 3: Kill Process

```bash
# Encontrar o PID
ps aux | grep nokia_gateway.py

# Parar graciosamente (SIGTERM)
kill <PID>

# Força (não recomendado)
kill -9 <PID>
```

### Método 4: pkill

```bash
pkill -f nokia_gateway.py
```

## Estrutura do Projeto

```
nokia_api/
├── venv/                      # Virtual environment
├── certs/                     # Certificados SSL
│   ├── ca.crt
│   ├── nfmt.pem
│   └── key.pem
├── logs/                      # Arquivos de log
│   ├── application.log
│   ├── error.log
│   └── kafka_messages.jsonl
├── nokia_gateway.py           # Aplicação FastAPI principal
├── token_manager.py           # Gerenciamento de tokens OAuth
├── alarm_manager.py           # Orquestrador de alarmes
├── alarm_subscription.py      # API de subscrição Nokia
├── kafka_consumer.py          # Consumer Kafka com SSL
├── jsonl_handler.py           # Exportador JSONL
├── log_config.py              # Configuração de logging
├── requirements.txt           # Dependências Python
├── .env                       # Configurações (não commitar)
├── .gitignore                # Arquivos ignorados pelo Git
└── README.md                 # Esta documentação
```

## Módulos Principais

### nokia_gateway.py (Main Application)

FastAPI application com lifespan management:
- Inicializa token_manager e alarm_manager no startup
- Para serviços graciosamente no shutdown
- Define todos os endpoints REST

**Principais funções:**
- `lifespan()`: Context manager para startup/shutdown
- `get_trail_list()`: Proxy para Nokia API trail endpoint
- `get_alarm_status()`: Status do alarm manager
- `shutdown()`: Endpoint para parar a aplicação

### token_manager.py (Token Management)

Singleton pattern para gerenciamento de tokens:
- `get_initial_token()`: Obtém token inicial com Basic Auth
- `refresh_access_token()`: Renova token usando refresh_token
- `start_auto_refresh()`: Inicia refresh automático em background
- `get_authorization_header()`: Retorna header Authorization

**Threading:** Daemon thread executa refresh a cada 3000 segundos (50 min)

### alarm_manager.py (Alarm Orchestration)

Orquestra subscription e Kafka consumer:
- `initialize()`: Cria subscrição e inicia Kafka consumer
- `get_status()`: Retorna status de subscrição e consumer
- `shutdown()`: Para consumer e renewal thread
- `_renewal_worker()`: Background thread para renovar subscrição

**Threading:** Daemon thread renova subscrição a cada 1800 segundos (30 min)

### alarm_subscription.py (Nokia Subscription API)

Gerencia subscrições de alarmes na API Nokia:
- `create_subscription()`: Cria nova subscrição para NSP-FAULT
- `renew_subscription()`: Renova subscrição existente
- `delete_subscription()`: Remove subscrição

### kafka_consumer.py (Kafka Consumer)

Consumer Kafka com SSL/TLS:
- `create_consumer()`: Cria consumer com SSL context
- `start_consuming()`: Inicia consumo em background thread
- `stop_consuming()`: Para consumer graciosamente
- `_consume_worker()`: Worker thread que processa mensagens

**SSL Configuration:**
- SSL Protocol: SSL/TLS
- Client certificates: nfmt.pem + key.pem
- CA certificate: ca.crt
- Hostname verification: Disabled

### jsonl_handler.py (JSONL Export)

Handler para exportar mensagens Kafka:
- `write_message()`: Escreve mensagem no arquivo JSONL
- `get_message_count()`: Conta total de mensagens
- `get_file_size()`: Retorna tamanho do arquivo
- `clear_file()`: Limpa o arquivo JSONL

### log_config.py (Logging Configuration)

Configuração centralizada de logging:
- `LogConfig.initialize()`: Configura handlers rotativos
- Cria diretório logs/ automaticamente
- RotatingFileHandler para application.log e error.log
- Formatação consistente com timestamps

## Fluxo de Autenticação

### 1. Token Inicial
```
POST /auth/token
Authorization: Basic base64(username:password)
Content-Type: application/json

Body: {"grant_type": "client_credentials"}

Response:
{
  "access_token": "VEtOLW1ub...",
  "refresh_token": "UkVUS04tbW5v...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

### 2. Auto-Refresh (Background)
```
POST /auth/token
Content-Type: application/json

Body:
{
  "grant_type": "refresh_token",
  "refresh_token": "UkVUS04tbW5v..."
}

Response: Same as initial token
```

### 3. Requisições Autenticadas
```
GET /oms1350/data/npr/trails/{network_id}
Authorization: Bearer VEtOLW1ub...
```

## Troubleshooting

### Gateway não inicia

**Problema:** `ModuleNotFoundError: No module named 'log_config'`

**Solução:**
```bash
# Verificar se todos os arquivos estão presentes
ls -la *.py

# Reinstalar dependências
pip install -r requirements.txt
```

### Erro de SSL no Kafka

**Problema:** `SSL: CERTIFICATE_VERIFY_FAILED` ou `No such file or directory: 'certs/...'`

**Solução:**
1. Verificar se certificados existem em `certs/`:
```bash
ls -la certs/
```

2. Verificar paths no `.env`:
```bash
CA=certs/ca.crt
KEY=certs/key.pem
PEM_CERT=certs/nfmt.pem
```

3. Verificar formato dos certificados (devem ser PEM):
```bash
openssl x509 -in certs/ca.crt -text -noout
```

### Kafka não recebe mensagens

**Problema:** Consumer conectado mas sem mensagens

**Solução:**
1. Verificar status da subscrição:
```bash
curl http://localhost:6778/api/v1/nokia_gateway/alarm_status
```

2. Verificar logs para subscription ID e topic ID:
```bash
tail -f logs/application.log | grep -i subscription
```

3. Forçar renovação de subscrição (restart do gateway):
```bash
curl -X POST http://localhost:6778/shutdown
python nokia_gateway.py
```

### Token expirado (401 Unauthorized)

**Problema:** Requisições falham com erro 401

**Solução:**
1. Verificar logs de refresh:
```bash
tail -f logs/application.log | grep -i token
```

2. Verificar validade do token:
```bash
curl http://localhost:6778/health
```

3. Forçar refresh (restart):
```bash
curl -X POST http://localhost:6778/shutdown
python nokia_gateway.py
```

### Arquivo JSONL corrompido

**Problema:** Erro ao ler `kafka_messages.jsonl`

**Solução:**
```bash
# Verificar última linha (deve ser JSON válido)
tail -n 1 logs/kafka_messages.jsonl | python -m json.tool

# Contar mensagens
wc -l logs/kafka_messages.jsonl

# Limpar arquivo (CUIDADO: apaga todos os eventos)
> logs/kafka_messages.jsonl
```

### Logs rotacionais não funcionam

**Problema:** Apenas um arquivo de log sem backups

**Solução:**
1. Verificar configuração no `.env`:
```bash
LOG_MAX_BYTES=10485760      # 10MB
LOG_BACKUP_COUNT=10
```

2. Verificar permissões do diretório logs:
```bash
ls -ld logs/
chmod 755 logs/
```

3. Forçar rotação (criar logs grandes):
```bash
# Verificar tamanho atual
ls -lh logs/application.log
```

### Gateway consome muita memória

**Problema:** Uso de memória cresce continuamente

**Solução:**
1. Verificar tamanho do arquivo JSONL:
```bash
ls -lh logs/kafka_messages.jsonl
```

2. Limpar arquivo JSONL periodicamente (criar cron job):
```bash
# Adicionar ao crontab: limpar todo dia às 00:00
0 0 * * * > /path/to/logs/kafka_messages.jsonl
```

3. Ajustar auto_offset_reset no Kafka consumer se necessário

### Múltiplas instâncias rodando

**Problema:** Gateway iniciado múltiplas vezes

**Solução:**
```bash
# Listar todos os processos
ps aux | grep nokia_gateway.py

# Matar todos os processos
pkill -f nokia_gateway.py

# Verificar porta 6778
lsof -i :6778

# Matar processo na porta 6778
kill -9 $(lsof -t -i:6778)
```

## Testando a Aplicação

### 1. Verificar Health

```bash
curl http://localhost:6778/health
```

Deve retornar:
```json
{
  "status": "healthy",
  "service": "Nokia Gateway API",
  "token_valid": true
}
```

### 2. Testar Trail List

```bash
curl "http://localhost:6778/api/v1/nokia_gateway/trail_list?network_id=788602"
```

### 3. Verificar Status de Alarmes

```bash
curl http://localhost:6778/api/v1/nokia_gateway/alarm_status
```

### 4. Monitorar Logs em Tempo Real

```bash
# Logs gerais
tail -f logs/application.log

# Apenas mensagens Kafka
tail -f logs/application.log | grep -i kafka

# Eventos JSONL
tail -f logs/kafka_messages.jsonl | while read line; do echo "$line" | python -m json.tool; done
```

### 5. Contar Eventos Capturados

```bash
# Total de eventos
wc -l logs/kafka_messages.jsonl

# Eventos nas últimas 24h (exemplo)
grep "$(date -d '24 hours ago' '+%Y-%m-%d')" logs/kafka_messages.jsonl | wc -l
```

## Notas Importantes

- O gateway desabilita verificação SSL para certificados auto-assinados da Nokia API
- Todos os serviços (token refresh, alarm renewal, Kafka consumer) rodam em threads daemon
- Use `Ctrl+C` ou `POST /shutdown` para parar graciosamente
- Tokens expiram em 3600 segundos (60 minutos) mas são renovados a cada 3000 segundos (50 minutos)
- Subscrições são renovadas a cada 30 minutos para evitar expiração
- Kafka consumer usa SSL/TLS com autenticação via certificados cliente
- Mensagens Kafka são exportadas para JSONL em append mode (nunca sobrescreve)
- Logs rotativos garantem que não ocupem espaço infinito (max 100MB total)

## Segurança

- **Certificados:** Mantenha `certs/` fora do Git (.gitignore)
- **Credenciais:** Nunca commite o arquivo `.env` com senhas reais
- **SSL:** Certificados devem ter permissões restritas (600):
  ```bash
  chmod 600 certs/*.pem certs/*.key
  ```
- **Passphrase:** Armazene passphrase do certificado no `.env`, não hardcode
- **API Token:** Tokens são armazenados em memória, nunca em disco
- **Logs:** Arquivos de log podem conter informações sensíveis, restrinja acesso:
  ```bash
  chmod 700 logs/
  ```

## Desativar Virtual Environment

```bash
deactivate
```

## Licença

Este projeto é proprietário e confidencial.
