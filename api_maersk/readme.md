# 📦 Sistema de Sincronização de Disputas - Maersk API

Sistema automatizado para sincronização de disputas de invoices do portal Maersk com banco de dados MySQL.

---

## 📋 Índice

1. [Visão Geral](#visão-geral)
2. [Arquitetura do Sistema](#arquitetura-do-sistema)
3. [Estrutura do Projeto](#estrutura-do-projeto)
4. [Funcionalidades Principais](#funcionalidades-principais)
5. [Como Executar](#como-executar)
6. [Banco de Dados](#banco-de-dados)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Visão Geral

O sistema realiza três funções principais:

### **1. Gerenciamento de Tokens**
- Carrega tokens do arquivo `artifacts/maersk_all_tokens.json`
- Valida se o token está expirado
- Renova automaticamente via Selenium quando necessário
- Salva novo token no arquivo

### **2. Sincronização de Disputas**
- Busca todas as disputas da API Maersk
- Consulta invoices do banco de dados MySQL
- Faz match entre invoices e disputas
- Salva/atualiza disputas no banco com informações completas

### **3. Atualização de Status**
- Busca uma disputa específica por ID
- Consulta informações atualizadas na API
- Atualiza status e dados no banco de dados

---

## 🏗️ Arquitetura do Sistema

```
┌─────────────────────────────────────────────────────────┐
│                    FLUXO DO SISTEMA                     │
└─────────────────────────────────────────────────────────┘

1. TOKEN SERVICE
   ├─ Carrega token do arquivo
   ├─ Valida expiração (JWT decode)
   ├─ Se expirado → Chama AUTH SERVICE
   └─ Retorna token válido

2. AUTH SERVICE (Selenium)
   ├─ Abre navegador Chrome
   ├─ Faz login no portal Maersk
   ├─ Seleciona cada customer
   ├─ Captura novos tokens
   └─ Salva no arquivo JSON

3. DISPUTE SERVICE
   ├─ Consulta API Maersk (/disputes-external)
   ├─ Lista todas as disputas
   ├─ Busca detalhes de disputa específica
   └─ Retorna dados formatados

4. SYNC SERVICE
   ├─ Orquestra todo o processo
   ├─ Busca invoices do banco
   ├─ Faz match com disputas da API
   └─ Salva/atualiza no banco

5. REPOSITORIES
   ├─ invoice_repository → Consulta invoices
   └─ disputa_repository → Salva/atualiza disputas
```

---

## 📂 Estrutura do Projeto

```
api_maersk/
│
├── config/
│   ├── settings.py              # Configurações (DB, API, URLs)
│   └── __init__.py
│
├── services/
│   ├── token_service.py         # Gerenciamento de tokens
│   ├── auth_service.py          # Autenticação via Selenium
│   ├── dispute_service.py       # Comunicação com API Maersk
│   ├── dispute_sync_service.py  # Orquestração da sincronização
│   └── __init__.py
│
├── repos/
│   ├── invoice_repository.py    # Consultas de invoices
│   ├── disputa_repository.py    # CRUD de disputas
│   └── __init__.py
│
├── utils/
│   ├── logger.py                # Configuração de logs
│   └── __init__.py
│
├── tests/
│   ├── sync_disputes.py         # ⭐ SCRIPT PRINCIPAL
│   ├── test_token.py            # Testa validação de tokens
│   ├── test_auth.py             # Renova tokens manualmente
│   ├── test_dispute.py          # Testa consulta de disputas
│   └── test_update_dispute.py   # Atualiza disputa específica
│
├── artifacts/
│   └── maersk_all_tokens.json   # Tokens salvos
│
└── .env                         # Credenciais (não versionar!)
```

---

## ⚙️ Funcionalidades Principais

### **1️⃣ Função Token**

**Arquivo:** `services/token_service.py`

**Fluxo:**
1. Carrega token do arquivo JSON
2. Decodifica JWT e verifica expiração
3. Se expirado → Chama renovação automática
4. Salva novo token no arquivo
5. Retorna token válido

**Método:** `get_valid_token(customer_code, auth_service)`

---

### **2️⃣ Função Disputas (Sincronização)**

**Arquivo:** `services/dispute_sync_service.py`

**Fluxo:**
1. Lista **TODAS** as disputas da API (337 no momento)
2. Busca invoices MAERSK do banco de dados
3. Cria mapa: `{invoice_number: dispute_data}`
4. Para cada invoice do banco:
   - Verifica se tem disputa na API
   - Se sim → Salva/atualiza no banco
   - Se não → Log "sem disputa"

**Método:** `sync_disputes(customer_code, limit)`

**Dados salvos:**
- `dispute_number` - ID da disputa
- `status` - Status atual (New, In Review, etc)
- `dispute_reason` - Motivo da disputa
- `disputed_amount` - Valor disputado
- `currency` - Moeda (USD, BRL, etc)
- `api_created_date` - Data de criação na API
- `api_last_modified` - Última modificação na API

---

### **3️⃣ Função Status**

**Arquivo:** `services/dispute_sync_service.py`

**Fluxo:**
1. Recebe `dispute_id` como parâmetro
2. Chama `get_valid_token()` (automático)
3. Busca dados atualizados na API
4. Encontra `invoice_id` no banco
5. Atualiza registro da disputa

**Método:** `update_dispute_status(dispute_id, customer_code)`

---

## 🚀 Como Executar

### **Pré-requisitos**

1. Python 3.8+
2. MySQL rodando
3. Arquivo `.env` configurado:

```env
# Credenciais Maersk
MAERSK_USERNAME=seu_usuario
MAERSK_PASSWORD=sua_senha

# Banco de Dados
DB_HOST=localhost
DB_PORT=3306
DB_NAME=feat_pc
DB_USER=root
DB_PASSWORD=sua_senha
```

4. Instalar dependências:
```bash
pip install mysql-connector-python selenium webdriver-manager python-dotenv pyjwt
```

---

### **Execução - Passo a Passo**

#### **1. Sincronizar Disputas (Principal)**

```bash
py tests/sync_disputes.py
```

**O que acontece:**
- ✅ Valida/renova token automaticamente
- ✅ Busca 337 disputas da API
- ✅ Consulta invoices do banco
- ✅ Salva disputas encontradas

**Saída esperada:**
```
2025-09-30 11:20:44 [INFO] Encontradas 337 disputas na API
2025-09-30 11:20:44 [INFO] Encontradas 2 invoices no banco
2025-09-30 11:20:44 [INFO] Invoice 7536709258 tem disputa 23724918 | Status: New | Valor: -325.0 USD
2025-09-30 11:20:44 [INFO] Disputa 23724918 salva/atualizada
2025-09-30 11:20:44 [INFO] SINCRONIZAÇÃO CONCLUÍDA
2025-09-30 11:20:44 [INFO] Total de invoices: 2
2025-09-30 11:20:44 [INFO] Com disputa: 1
2025-09-30 11:20:44 [INFO] Sem disputa: 1
```

**Configurar quantidade de invoices:**
Editar `tests/sync_disputes.py` linha 21:
```python
sync_service.sync_disputes(customer_code="305S3073SPA", limit=100)
#                                                         ↑ Alterar aqui
```

---

#### **2. Renovar Tokens Manualmente**

```bash
py tests/test_auth.py
```

**Quando usar:**
- Tokens expiraram e renovação automática falhou
- Quer renovar antes de expirar

**O que acontece:**
- Abre navegador Chrome
- Faz login automaticamente
- Captura tokens de todos os 5 customers
- Salva em `artifacts/maersk_all_tokens.json`

⚠️ **Atenção:** Navegador abre visível (não fechar manualmente)

---

#### **3. Atualizar Disputa Específica**

```bash
py tests/test_update_dispute.py
```

**Editar o arquivo para mudar a disputa:**
```python
dispute_id = "23724918"  # ← Alterar aqui
customer_code = "305S3073SPA"
```

**O que acontece:**
- Busca dados atualizados da disputa na API
- Atualiza status e valores no banco

---

#### **4. Testar Token Válido**

```bash
py tests/test_token.py
```

**O que faz:**
- Carrega tokens do arquivo
- Valida se estão expirados
- Mostra tempo restante
- Testa conversão de códigos

---

## 🗄️ Banco de Dados

### **Tabela: `invoice`**

```sql
CREATE TABLE `invoice` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `armador` enum('MAERSK','HAPAG'),
  `numero_invoice` varchar(191),
  `data_emissao_invoice` datetime(3),
  `data_vencimento` datetime(3),
  `numero_bl` varchar(191),
  `origem` varchar(191),
  `destino` varchar(191),
  `created_at` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` datetime(3),
  -- ... outros campos
);
```

### **Tabela: `disputa`**

```sql
CREATE TABLE `disputa` (
  `id` int PRIMARY KEY AUTO_INCREMENT,
  `invoice_id` int NOT NULL,
  `dispute_number` bigint,
  `status` varchar(50) NOT NULL,
  
  -- Campos da API Maersk
  `dispute_reason` varchar(100),
  `disputed_amount` decimal(15,2),
  `currency` varchar(10),
  `api_created_date` datetime(3),
  `api_last_modified` datetime(3),
  
  `created_at` datetime(3) DEFAULT CURRENT_TIMESTAMP(3),
  `updated_at` datetime(3) DEFAULT CURRENT_TIMESTAMP(3) ON UPDATE CURRENT_TIMESTAMP(3),
  
  UNIQUE KEY `uq_disputa_invoice_disputenumber` (`invoice_id`, `dispute_number`),
  KEY `idx_disputa_status` (`status`),
  KEY `idx_disputa_number` (`dispute_number`),
  
  CONSTRAINT `fk_disputa_invoice` 
    FOREIGN KEY (`invoice_id`) REFERENCES `invoice` (`id`)
);
```

### **Consultar Disputas Salvas**

```sql
SELECT 
    d.id,
    d.dispute_number,
    d.status,
    d.dispute_reason,
    d.disputed_amount,
    d.currency,
    i.numero_invoice,
    i.armador,
    d.created_at,
    d.updated_at
FROM disputa d
INNER JOIN invoice i ON i.id = d.invoice_id
WHERE d.status = 'New'  -- Filtrar por status
ORDER BY d.updated_at DESC
LIMIT 10;
```

---

## 🔧 Troubleshooting

### **Problema: Token expirado e renovação falha**

**Erro:**
```
Token expirado para 305S3073SPA
Falha ao renovar token
```

**Solução:**
```bash
py tests/test_auth.py
```
Aguardar renovação manual (1-2 minutos)

---

### **Problema: Erro de conexão com banco**

**Erro:**
```
mysql.connector.errors.ProgrammingError: Access denied for user
```

**Solução:**
1. Verificar credenciais no `.env`
2. Testar conexão no DBeaver
3. Verificar se MySQL está rodando

---

### **Problema: Nenhuma disputa encontrada**

**Log:**
```
Encontradas 0 disputas na API
```

**Possíveis causas:**
1. Token inválido → Renovar tokens
2. Customer code errado → Verificar `CUSTOMER_CODE_MAPPING` em `settings.py`
3. API fora do ar → Testar manualmente no portal

---

### **Problema: Invoice não encontrada no banco**

**Log:**
```
Invoice 7536709258 não encontrada no banco
```

**Solução:**
Inserir invoice no banco:
```sql
INSERT INTO invoice (armador, numero_invoice, created_at, updated_at)
VALUES ('MAERSK', '7536709258', NOW(3), NOW(3));
```

---

## 📊 Estatísticas e Monitoramento

### **Query: Resumo de Disputas**

```sql
SELECT 
    status,
    COUNT(*) as total,
    SUM(disputed_amount) as valor_total,
    currency
FROM disputa
GROUP BY status, currency
ORDER BY total DESC;
```

### **Query: Disputas Recentes**

```sql
SELECT 
    i.numero_invoice,
    d.dispute_number,
    d.status,
    d.disputed_amount,
    d.currency,
    d.updated_at
FROM disputa d
INNER JOIN invoice i ON i.id = d.invoice_id
WHERE d.updated_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY d.updated_at DESC;
```

---

## 📝 Notas Importantes

### **Tokens**
- Duração: ~12 horas
- Renovação: Automática quando expirado
- Arquivo: `artifacts/maersk_all_tokens.json`
- ⚠️ **NÃO versionar este arquivo!**

### **Customers**
O sistema gerencia 5 customers:
1. `30501112445`
2. `30501348288`
3. `30501348218`
4. `305S3073SPA` ← Principal
5. `30501113841`

### **API Maersk**
- Base URL: `https://api.maersk.com`
- Consumer Key: `mWGhMttfQt4mvDiTBqoAfM8Sd0tyiZrj`
- Rate Limit: Não documentado
- Timeout: 30 segundos

---

## 🎯 Resumo Executivo

### **Para Executar o Sistema Completo:**

```bash
# 1. Sincronizar disputas
py tests/sync_disputes.py

# Resultado: Disputas atualizadas no banco
```

### **Resultado Esperado:**

| Métrica | Valor |
|---------|-------|
| Disputas na API | 337 |
| Invoices no Banco | Variável |
| Disputas Salvas | Match encontrados |
| Taxa de Sucesso | 100% |
| Tempo de Execução | ~2-5 segundos |

### **Campos Salvos por Disputa:**

✅ Número da disputa  
✅ Status atual  
✅ Motivo da disputa  
✅ Valor disputado  
✅ Moeda  
✅ Data de criação na API  
✅ Última modificação na API  

---

## 👨‍💻 Desenvolvido por

**Henrique SA**  
Projeto: Sistema de Sincronização de Disputas Maersk  
Data: Setembro 2025

---

## 📞 Suporte

Para dúvidas ou problemas:
1. Verificar logs no console
2. Consultar seção [Troubleshooting](#troubleshooting)
3. Testar componentes individualmente (tests/)
4. Verificar conexão API e banco de dados