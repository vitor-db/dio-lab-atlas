# Base de Conhecimento

> Esta seção descreve os dados que alimentam o Atlas, a lógica de conciliação que os transforma em fonte analítica, e a narrativa embutida para tornar o protótipo demonstrável.

---

## Sumário

- [Visão Geral](#visão-geral)
- [Arquitetura de Ingestão](#arquitetura-de-ingestão)
- [Arquivos de Dados](#arquivos-de-dados)
- [Camada de Conciliação](#camada-de-conciliação)
- [Narrativa dos Dados](#narrativa-dos-dados)
- [Como o Agente Consome os Dados](#como-o-agente-consome-os-dados)
- [Disclaimer](#disclaimer)

---

## Visão Geral

A base de conhecimento do Atlas é uma simulação deliberada da arquitetura de dados que existiria em produção, num banco que ofereça este tipo de solução em IA aos seus clientes PJ.

Os arquivos estão organizados em duas camadas lógicas:

| Camada | Representa | Arquivos |
|---|---|---|
| **Fontes brutas** | O que viria de integrações reais (Open Finance, CRM, SEFAZ) | `extrato_bancario.csv`, `mapeamento_clientes.csv` |
| **Dados complementares** | Contexto do cliente PJ analisado | `perfil_empresa.json`, `produtos_financeiros.json`, `historico_atendimento.csv` |

---

## Arquitetura de Ingestão

### Arquitetura-alvo (produção)

Numa implementação real, o Atlas teria duas fontes automatizadas:

| Fonte | O que entrega |
|---|---|
| **Open Finance** | Extrato bancário em tempo real — data, valor, remetente, modalidade |
| **CRM do banco + SEFAZ** | Enriquecimento: quem é o CNPJ do remetente, qual solução em IA foi prestado (via NFs), qual canal trouxe o cliente |

Essas duas fontes são cruzadas por uma camada de conciliação para gerar o **dado enriquecido** — que é o que a engine analítica consome.

### Simulação (este projeto)

| Camada em produção | Representada neste projeto por |
|---|---|
| Open Finance | `data/extrato_bancario.csv` |
| CRM + SEFAZ | `data/mapeamento_clientes.csv` |
| solução em IA de conciliação automatizada | `src/conciliacao.py` |

A estrutura dos CSVs foi desenhada para espelhar o que essas integrações realmente retornariam. Isso torna o protótipo mais próximo de uma arquitetura implementável.

---

## Arquivos de Dados

### `extrato_bancario.csv`

Simula o retorno do **Open Finance** — dado bruto, sem enriquecimento semântico.

| Campo | Tipo | Descrição |
|---|---|---|
| `data` | date | Data da transação |
| `descricao` | string | Descrição bruta (ex: *"PIX RECEBIDO - ALPHA GESTAO EMPRESARIAL"*) |
| `cnpj_remetente` | string | CNPJ de quem enviou o valor |
| `modalidade` | string | PIX, TED, boleto |
| `valor` | float | Valor da transação |
| `tipo` | string | `receita` ou `inadimplencia` |

> Importante: o extrato **não sabe** quem é o cliente, qual categoria de solução em IA ou canal. Esses metadados são adicionados pela conciliação.

### `mapeamento_clientes.csv`

Simula o enriquecimento via **CRM + SEFAZ**. Numa arquitetura real, viria do cruzamento de NFs emitidas (que identificam CNPJ, cliente e solução em IA) com os registros do banco.

| Campo | Tipo | Descrição |
|---|---|---|
| `cnpj` | string | CNPJ do cliente |
| `client_id` | string | ID interno (CLI-001, CLI-002, etc.) |
| `nome_cliente` | string | Razão social |
| `categoria` | string | Tipo de solução em IA prestado (consultoria, implementação, licença, suporte) |
| `canal` | string | Canal de aquisição (indicação, licitação, prospecção ativa, parceiros) |

### `perfil_empresa.json`

Dados da empresa analisada pelo Atlas — neste protótipo, a fictícia **Nexus Soluções Corporativas Ltda**.

Campos principais: razão social, CNPJ, segmento, porte, região, canais de aquisição, ticket médio, base de clientes ativa, metas estratégicas (receita anual, expansão de base, etc.).

As metas são especialmente importantes: permitem que o Atlas compare realidade vs. alvo e responda "você está a X% da meta".

### `produtos_financeiros.json`

Catálogo de produtos que o **banco** oferece à empresa analisada. Usado como referência para recomendações contextuais — por exemplo, se o Atlas identifica alta reserva ociosa, pode sugerir produtos de aplicação compatíveis.

### `historico_atendimento.csv`

Histórico de interações entre a empresa e o banco. Usado para análises operacionais (tickets em aberto, recorrência de problemas).

| Campo | Tipo | Descrição |
|---|---|---|
| `ticket_id` | string | Identificador do atendimento |
| `data` | date | Data do contato |
| `tipo` | string | Categoria do chamado |
| `descricao` | string | Detalhamento |
| `status` | string | Resolvido / Em andamento / Pendente |

---

## Camada de Conciliação

O arquivo `src/conciliacao.py` é o componente que une as duas fontes brutas e produz o dado enriquecido.

```python
extrato_bancario.csv  ──┐
                         ├──▶ conciliacao.py ──▶ DataFrame enriquecido
mapeamento_clientes.csv ─┘
```

O resultado é um DataFrame único com todos os campos: `data`, `client_id`, `nome_cliente`, `categoria`, `canal`, `modalidade`, `valor`, `tipo`.

Esse DataFrame é o que a engine analítica consome. Essa separação reflete o que existiria num sistema real e isola a lógica de enriquecimento do cálculo.

---

## Narrativa dos Dados

Foram construídos deliberadamente para que o Atlas tenha **algo de valor a diagnosticar**.

### Padrões intencionalmente embutidos

| Padrão | Como se manifesta nos dados |
|---|---|
| **Concentração de receita** | ~61% da receita vem dos 3 maiores clientes (Alpha, Beta, Epsilon) — aciona a análise de risco de dependência |
| **Inadimplência pontual** | 2 eventos em clientes distintos (CLI-003 e CLI-005) — permite calcular impacto e identificar reincidência |
| **Crescimento via indicação** | Canal `indicacao` domina em valor (44% da receita), sugerindo que é o motor de aquisição mais eficiente |
| **Sazonalidade Q4** | Receita cresce no segundo semestre — projetos e renovações concentrados em set/out/nov/dez |
| **Meta superada** | Receita atual supera a meta anual — permite ao Atlas responder com projeção e recomendação de revisão |
| **Operacional com pontos abertos** | Alguns tickets de atendimento não resolvidos — sinal de atenção em integração |

---

## Como o Agente Consome os Dados

### Carga

A função `carregar_dados()` em `src/agente.py` faz três coisas:

1. Lê `extrato_bancario.csv` e `mapeamento_clientes.csv`
2. Chama `conciliar()` para gerar o DataFrame enriquecido
3. Lê `perfil_empresa.json` e `historico_atendimento.csv`



```python
{
    "transacoes": DataFrame,   # dado enriquecido, fonte analítica principal
    "perfil": dict,            # perfil da empresa, metas
    "atendimento": DataFrame,  # histórico operacional
}
```

### Uso no prompt

Os dados **não são injetados diretamente no system prompt** — isso causaria custo alto e risco de alucinação.

Em vez disso:

1. A engine analítica (pandas) consome o dicionário e produz um JSON estruturado com **apenas os resultados relevantes à pergunta**
2. O LLM recebe esse JSON como contexto, com a instrução explícita: *"use APENAS os números presentes no JSON fornecido"*
3. O LLM traduz o JSON em linguagem natural

Ou seja: o LLM nunca lê os dados brutos. Ele só enxerga o que a engine já calculou.

### Exemplo de JSON enviado ao LLM

```json
{
  "analise": "concentracao_receita",
  "receita_total": 4544300.00,
  "top_clientes": [
    {"cliente": "Alpha Gestão Empresarial", "receita": 1245000.00, "pct": 27.4},
    {"cliente": "Beta Sistemas Ltda", "receita": 913000.00, "pct": 20.1},
    {"cliente": "Epsilon Indústria Ltda", "receita": 613000.00, "pct": 13.5}
  ],
  "pct_top3": 61.0,
  "qtd_clientes_ativos": 11
}
```

O Atlas interpreta e gera uma resposta como:

> *"61% da sua receita está concentrada em 3 clientes (Alpha, Beta e Epsilon). Alpha sozinho representa 27%. Essa concentração é um risco operacional relevante — uma perda de Alpha comprometeria mais de um quarto do faturamento anual."*

---

## Disclaimer

Os dados utilizados neste projeto são **fictícios**. Foram construídos para fins de estudo com padrões narrativos intencionais que permitem demonstrar a capacidade analítica do Atlas.

Os arquivos `extrato_bancario.csv` e `mapeamento_clientes.csv` simulam, respectivamente, o retorno de uma integração Open Finance e um enriquecimento via CRM/SEFAZ — sem estar conectados a nenhum sistema real.

---

*Projeto de estudos — escopo simulado, sem integração com sistemas em produção.*