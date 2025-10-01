# API Maersk - Sistema de Gestão de Disputas

Sistema para sincronização e gerenciamento de disputas de invoices da Maersk.

## Funcionalidades

- Sincronização automática de disputas
- Gerenciamento de tokens com renovação automática
- Importação de invoices faltantes
- Atualização de status de disputas
- Suporte a múltiplos clientes

## Instalação

1. Clone o repositório
2. Instale as dependências: pip install -r requirements.txt
3. Configure o arquivo .env

## Uso

Menu interativo: python main.py

Scripts individuais:
- python scripts/sync_disputes.py
- python scripts/sync_all_customers.py

## Estrutura

api_maersk/
- config/ - Configurações
- repos/ - Repositórios
- services/ - Lógica de negócio
- scripts/ - Scripts de produção
- main.py - Ponto de entrada

## Requisitos

- Python 3.8+
- MySQL 5.7+
