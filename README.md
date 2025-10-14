# Nokia API Authentication Client

Cliente Python para autenticação e gerenciamento de tokens da API Nokia com refresh automático.

## Características

- ✅ Autenticação básica para obter token inicial
- ✅ Refresh automático de token a cada 60 minutos
- ✅ Thread em background para renovação automática
- ✅ Método helper para requisições autenticadas (GET, POST, PUT, DELETE)
- ✅ Tratamento de certificados SSL auto-assinados
- ✅ Sistema de logging configurado

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

### 3. Configurar Credenciais

Edite o arquivo `.env` com suas credenciais:

```bash
API_BASE_URL=https://10.73.0.181/rest-gateway/rest/api/v1
API_USERNAME=api_user
API_PASSWORD=api_user@
TOKEN_REFRESH_INTERVAL=3600
```

## Uso

### Exemplo Básico

```python
from nokia_api_auth import NokiaAPIAuth

# Inicializar o gerenciador de autenticação
auth = NokiaAPIAuth(
    base_url="https://10.73.0.181/rest-gateway/rest/api/v1",
    username="api_user",
    password="api_user@"
)

# Obter token inicial
token_data = auth.get_initial_token()
print(f"Access Token: {auth.access_token}")

# Iniciar refresh automático a cada 60 minutos (3600 segundos)
auth.start_auto_refresh(refresh_interval=3600)

# Fazer requisições autenticadas
response = auth.make_authenticated_request('GET', '/some/endpoint')
```

### Executar o Programa Principal

```bash
python nokia_api_auth.py
```

### Fazer Requisições Autenticadas

```python
from nokia_api_auth import NokiaAPIAuth

# Inicializar e autenticar
auth = NokiaAPIAuth(
    base_url="https://10.73.0.181/rest-gateway/rest/api/v1",
    username="api_user",
    password="api_user@"
)
auth.get_initial_token()
auth.start_auto_refresh()

# GET request
response = auth.make_authenticated_request('GET', '/your/endpoint')
print(f"Status: {response.status_code}")
print(f"Data: {response.json()}")

# POST request com dados
data = {"key": "value"}
response = auth.make_authenticated_request('POST', '/your/endpoint', json=data)

# PUT request
response = auth.make_authenticated_request('PUT', '/your/endpoint', json=data)

# DELETE request
response = auth.make_authenticated_request('DELETE', '/your/endpoint')

# Obter header de autorização manualmente
headers = auth.get_authorization_header()
# headers = {"Authorization": "Bearer VEtOLW1ub2d1..."}
```

## Estrutura do Projeto

```
nokia_api/
├── venv/                      # Virtual environment
├── nokia_api_auth.py          # Programa principal
├── requirements.txt           # Dependências Python
├── .env                       # Configurações (não commitar)
├── .env.example              # Exemplo de configuração
├── .gitignore                # Arquivos ignorados pelo Git
└── README.md                 # Este arquivo
```

## Fluxo de Autenticação

1. **Token Inicial**: Requisição POST com autenticação básica para obter `access_token` e `refresh_token`
2. **Auto-Refresh**: Thread em background renova o token a cada 60 minutos usando o `refresh_token`
3. **Requisições**: Todas as requisições usam o `access_token` atual no header `Authorization: Bearer <token>`

## API Endpoints

### Obter Token Inicial
```
POST /auth/token
Authorization: Basic (username:password)
Content-Type: application/json

Body:
{
    "grant_type": "client_credentials"
}

Response:
{
    "access_token": "VEtOLW1ub...",
    "refresh_token": "UkVUS04tbW5v...",
    "token_type": "Bearer",
    "expires_in": 3600
}
```

### Renovar Token
```
POST /auth/token
Content-Type: application/json

Body:
{
    "grant_type": "refresh_token",
    "refresh_token": "UkVUS04tbW5v..."
}
```

## Desativar Virtual Environment

```bash
deactivate
```

## Notas Importantes

- O programa desabilita verificação SSL para certificados auto-assinados
- O refresh automático roda em thread daemon
- Use `Ctrl+C` para parar o programa graciosamente
- Os tokens expiram em 3600 segundos (60 minutos)

## Troubleshooting

### Erro de SSL
Se encontrar erros de SSL, o programa já está configurado para ignorar verificação de certificados auto-assinados.

### Erro de Conexão
Verifique se a URL da API está acessível:
```bash
curl -k https://10.73.0.181/rest-gateway/rest/api/v1/auth/token
```

### Token Expirado
O programa renova automaticamente. Se encontrar erro 401, verifique os logs para ver se o refresh está funcionando.
