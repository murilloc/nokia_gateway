# Nokia Gateway API

API Gateway REST para a Nokia API com gerenciamento automático de tokens OAuth.

## Visão Geral

O Nokia Gateway é uma API REST construída com FastAPI que abstrai a complexidade da autenticação Nokia API, fornecendo endpoints REST simples para acessar recursos da gerência de rede Nokia sem a necessidade de gerenciar tokens manualmente.

### Características

- Gerenciamento automático de tokens OAuth
- Renovação automática de tokens em background (a cada 50 minutos)
- API REST moderna usando FastAPI
- Documentação interativa Swagger/OpenAPI
- Tratamento robusto de erros
- Validação de requisições com Pydantic
- Suporte para certificados SSL auto-assinados

## Arquitetura

### Componentes

1. **nokia_gateway.py** - Aplicação FastAPI principal com endpoints REST
2. **token_manager.py** - Módulo singleton para gerenciamento de tokens
   - Autenticação inicial via HTTP Basic Auth
   - Renovação automática em thread daemon
   - Thread-safe com locks
3. **test_gateway.py** - Suite de testes automatizados

### Fluxo de Autenticação

```
Startup → Get Initial Token → Start Background Refresh Thread
                                        ↓
                              Refresh Token Every 50min
                                        ↓
                              API Requests Use Current Token
```

## Instalação

### Pré-requisitos

- Python 3.12+
- Virtual environment configurado

### Instalar Dependências

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### Configuração

Certifique-se de que o arquivo `.env` contém:

```env
API_BASE_URL=https://10.73.0.181/rest-gateway/rest/api/v1
API_USERNAME=seu_usuario
API_PASSWORD=sua_senha
TOKEN_REFRESH_INTERVAL=3000
```

## Uso

### Iniciar o Gateway

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Iniciar servidor
python nokia_gateway.py
```

O servidor iniciará na porta **6778** e estará disponível em `http://localhost:6778`

### Endpoints Disponíveis

#### 1. Root Endpoint
```bash
GET http://localhost:6778/
```

Resposta:
```json
{
  "service": "Nokia Gateway API",
  "version": "1.0.0",
  "status": "running"
}
```

#### 2. Health Check
```bash
GET http://localhost:6778/health
```

Resposta:
```json
{
  "status": "healthy",
  "service": "Nokia Gateway API",
  "token_valid": true
}
```

#### 3. Trail List (Principal)
```bash
GET http://localhost:6778/api/v1/nokia_gateway/trail_list?network_id=788602
```

Parâmetros:
- `network_id` (obrigatório): ID da rede para consultar trails

Resposta: Lista de trails da rede
```json
[
  {
    "id": 788602,
    "className": "Trail",
    "guiLabel": "BSA SU PMJ SO...",
    "aEndPortLabel": "PSS32-PMJSO-01/...",
    "zEndPortLabel": "PSS32-BSASU-01/...",
    "operationalState": "OperationalState_enabled",
    ...
  }
]
```

### Documentação Interativa

FastAPI gera automaticamente documentação interativa:

- **Swagger UI**: http://localhost:6778/docs
- **ReDoc**: http://localhost:6778/redoc
- **OpenAPI Schema**: http://localhost:6778/openapi.json

### Exemplos de Uso

#### cURL

```bash
# Obter trail list
curl "http://localhost:6778/api/v1/nokia_gateway/trail_list?network_id=788602"

# Health check
curl http://localhost:6778/health
```

#### Python (requests)

```python
import requests

# Obter trail list
response = requests.get(
    "http://localhost:6778/api/v1/nokia_gateway/trail_list",
    params={"network_id": "788602"}
)

if response.status_code == 200:
    trails = response.json()
    print(f"Found {len(trails)} trails")
    for trail in trails:
        print(f"Trail ID: {trail['id']} - {trail['guiLabel']}")
```

#### JavaScript (fetch)

```javascript
// Obter trail list
const response = await fetch(
  'http://localhost:6778/api/v1/nokia_gateway/trail_list?network_id=788602'
);
const trails = await response.json();
console.log(`Found ${trails.length} trails`);
```

## Testes

Execute a suite de testes:

```bash
source venv/bin/activate
python test_gateway.py
```

Testes incluídos:
- Root endpoint
- Health check
- Trail list com network ID válido
- Trail list com network ID inválido (retorna lista vazia)

## Tratamento de Erros

O gateway retorna códigos HTTP apropriados:

- **200**: Sucesso
- **401**: Falha de autenticação
- **404**: Recurso não encontrado
- **500**: Erro interno do servidor
- **502**: Erro ao comunicar com Nokia API
- **503**: Serviço de autenticação indisponível
- **504**: Timeout ao comunicar com Nokia API

Exemplo de resposta de erro:
```json
{
  "error": "Authentication failed",
  "status_code": 401
}
```

## Monitoramento

### Logs

O gateway gera logs detalhados incluindo:
- Inicialização do token manager
- Obtenção e renovação de tokens
- Requisições recebidas
- Erros e exceções

### Health Check

Use o endpoint `/health` para monitorar o status do serviço e validade do token.

## Produção

### Considerações

1. **Segurança**:
   - Configure HTTPS com certificados válidos
   - Implemente autenticação/autorização no gateway
   - Use variáveis de ambiente seguras para credenciais

2. **Performance**:
   - Configure workers do Uvicorn: `uvicorn nokia_gateway:app --workers 4`
   - Use proxy reverso (nginx) para load balancing

3. **Monitoramento**:
   - Implemente logging centralizado
   - Configure alertas para falhas de autenticação
   - Monitore health check endpoint

### Exemplo de Deploy com Uvicorn

```bash
# Com múltiplos workers
uvicorn nokia_gateway:app --host 0.0.0.0 --port 6778 --workers 4

# Com reload (desenvolvimento)
uvicorn nokia_gateway:app --host 0.0.0.0 --port 6778 --reload
```

## Extensão

Para adicionar novos endpoints:

1. Adicione função no `nokia_gateway.py`:
```python
@app.get("/api/v1/nokia_gateway/novo_endpoint")
async def novo_endpoint(param: str = Query(...)):
    headers = token_manager.get_authorization_header()
    # Implementar lógica
    return response
```

2. Use o `token_manager` para obter headers de autenticação
3. Implemente tratamento de erros apropriado
4. Adicione testes em `test_gateway.py`

## Troubleshooting

### Problema: Token não é renovado

**Solução**: Verifique logs para erros na thread de renovação. Valide credenciais no `.env`.

### Problema: Erro 503 ao chamar endpoint

**Solução**: Gateway não conseguiu autenticar. Verifique conectividade com a Nokia API e credenciais.

### Problema: Timeout nas requisições

**Solução**: Aumente o timeout nas requisições ou verifique conectividade de rede com os servidores Nokia.

## Licença

Projeto interno - Nokia API Gateway
