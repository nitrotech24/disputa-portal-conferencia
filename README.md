

\### Pasta \*\*api\_hapag/\*\*



\* \*\*`\_\_init\_\_.py`\*\* → Arquivo que transforma a pasta `api\_hapag` em um módulo Python. Normalmente vazio.

\* \*\*`auth.py`\*\* → Funções para login na Hapag e captura do token de autenticação.

\* \*\*`consulta\_disputa.py`\*\* → Funções para consultar disputas específicas na API da Hapag.

\* \*\*`consulta\_invoice.py`\*\* → Funções para consultar disputas vinculadas a uma invoice na API da Hapag.

\* \*\*`consulta\_status.py`\*\* → Funções para atualizar o status detalhado de uma disputa (chama a API e faz update no DB).

\* \*\*`repos/disputa\_repo.py`\*\* → Funções de acesso ao banco para salvar/atualizar disputas.

\* \*\*`repos/invoice\_repo.py`\*\* → Funções de acesso ao banco para listar invoices.

\* \*\*`storage.py`\*\* → Utilitários para salvar/carregar tokens em arquivo local.

\* \*\*`sync\_disputas.py`\*\* → Rotina principal para sincronizar invoices do DB com disputas da API.

\* \*\*`token.py`\*\* → Gerencia o ciclo de vida do token: valida se ainda é válido e gera um novo quando expira.



---



\### Pasta \*\*tests/\*\*



\* \*\*`test\_disputa.py`\*\* → Script de teste para consultar uma disputa específica.

\* \*\*`test\_invoice\_api.py`\*\* → Script de teste para consultar disputas por invoice.

\* \*\*`test\_invoices.py`\*\* → Script para listar invoices do banco (usando `invoice\_repo`).

\* \*\*`test\_status.py`\*\* → Script para testar a função que atualiza status de uma disputa no DB.

\* \*\*`test\_sync.py`\*\* → Script que testa a sincronização de disputes do DB com a API.



---



\### Raiz do projeto



\* \*\*`main.py`\*\* → ponto de entrada do sistema (executa o fluxo principal).





