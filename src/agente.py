"""
Atlas - Engine Analítica + Wrapper LLM

Arquitetura:
    [Pergunta do usuário]
            |
            v
    [Roteador] -> decide qual análise rodar
            |
            v
    [Engine Analítica] -> pandas calcula
            |
            v
    [Wrapper LLM] -> interpreta em linguagem natural
            |
            v
    [Resposta]

Princípio: o LLM NUNCA calcula. Apenas interpreta o resultado estruturado.
"""

import json
from pathlib import Path
import pandas as pd

from conciliacao import conciliar
from config import MODO_SIMULADO, ANTHROPIC_API_KEY, MODELO_LLM

DATA_DIR = Path(__file__).parent.parent / "data"



# CARGA DE DADOS
#============================================================

def carregar_dados():
    """Carrega e concilia todos os dados necessários para o Atlas."""
    extrato = pd.read_csv(DATA_DIR / "extrato_bancario.csv")
    mapeamento = pd.read_csv(DATA_DIR / "mapeamento_clientes.csv")
    df = conciliar(extrato, mapeamento)

    with open(DATA_DIR / "perfil_empresa.json", encoding="utf-8") as f:
        perfil = json.load(f)

    atendimento = pd.read_csv(DATA_DIR / "historico_atendimento.csv")

    return {"transacoes": df, "perfil": perfil, "atendimento": atendimento}



# ENGINE ANALÍTICA (pandas puro)
#============================================================

# ENGINE ANALÍTICA (pandas puro)
#============================================================

def concentracao_receita(df: pd.DataFrame) -> dict:
    """Calcula concentração de receita por cliente (regra 80/20)."""
    receita = df[df["tipo"] == "receita"].groupby("nome_cliente")["valor"].sum()
    receita = receita.sort_values(ascending=False)
    total = receita.sum()

    top3 = receita.head(3)
    pct_top3 = (top3.sum() / total) * 100

    return {
        "analise": "concentracao_receita",
        "receita_total": round(total, 2),
        "top_clientes": [
            {"cliente": nome, "receita": round(v, 2), "pct": round(v / total * 100, 1)}
            for nome, v in top3.items()
        ],
        "pct_top3": round(pct_top3, 1),
        "qtd_clientes_ativos": int(receita.count()),
    }


def receita_por_categoria(df: pd.DataFrame) -> dict:
    """Agrega receita por categoria de serviço."""
    creditos = df[df["tipo"] == "receita"]
    por_cat = creditos.groupby("categoria")["valor"].sum().sort_values(ascending=False)
    total = por_cat.sum()

    return {
        "analise": "receita_por_categoria",
        "receita_total": round(total, 2),
        "categorias": [
            {"categoria": c, "receita": round(v, 2), "pct": round(v / total * 100, 1)}
            for c, v in por_cat.items()
        ],
    }


def receita_por_canal(df: pd.DataFrame) -> dict:
    """Agrega receita por canal de aquisição."""
    creditos = df[df["tipo"] == "receita"]
    por_canal = creditos.groupby("canal")["valor"].sum().sort_values(ascending=False)
    total = por_canal.sum()

    return {
        "analise": "receita_por_canal",
        "receita_total": round(total, 2),
        "canais": [
            {"canal": c, "receita": round(v, 2), "pct": round(v / total * 100, 1)}
            for c, v in por_canal.items()
        ],
    }


def evolucao_mensal(df: pd.DataFrame) -> dict:
    """Receita mês a mês para identificar sazonalidade e tendência."""
    creditos = df[df["tipo"] == "receita"].copy()
    creditos["data"] = pd.to_datetime(creditos["data"])
    creditos["mes"] = creditos["data"].dt.to_period("M").astype(str)

    mensal = creditos.groupby("mes")["valor"].sum().sort_index()
    variacao = mensal.pct_change().fillna(0) * 100

    return {
        "analise": "evolucao_mensal",
        "meses": [
            {"mes": m, "receita": round(v, 2), "variacao_pct": round(variacao[m], 1)}
            for m, v in mensal.items()
        ],
        "receita_total": round(mensal.sum(), 2),
        "media_mensal": round(mensal.mean(), 2),
    }


def inadimplencia(df: pd.DataFrame) -> dict:
    """Identifica eventos de inadimplência."""
    estornos = df[df["tipo"] == "inadimplencia"]
    creditos = df[df["tipo"] == "receita"]
    total_credito = creditos["valor"].sum()
    total_estorno = estornos["valor"].abs().sum()

    por_cliente = (
        estornos.groupby("nome_cliente")["valor"]
        .agg(["sum", "count"])
        .sort_values("sum")
    )

    return {
        "analise": "inadimplencia",
        "total_estornos": round(total_estorno, 2),
        "pct_sobre_receita": round(total_estorno / total_credito * 100, 2) if total_credito else 0,
        "eventos": int(len(estornos)),
        "clientes_envolvidos": [
            {"cliente": nome, "valor": round(abs(v["sum"]), 2), "ocorrencias": int(v["count"])}
            for nome, v in por_cliente.iterrows()
        ],
    }


def status_metas(df: pd.DataFrame, perfil: dict) -> dict:
    """Compara receita atual com metas declaradas no perfil."""
    receita_atual = df[df["tipo"] == "receita"]["valor"].sum()
    metas = perfil.get("metas", [])

    resultado = []
    for m in metas:
        if "receita" in m["meta"].lower():
            pct = (receita_atual / m["valor_alvo"]) * 100
            resultado.append({
                "meta": m["meta"],
                "valor_atual": round(receita_atual, 2),
                "valor_alvo": m["valor_alvo"],
                "pct_atingido": round(pct, 1),
                "prazo": m["prazo"],
            })

    return {"analise": "status_metas", "metas": resultado}


def atendimento_operacional(atendimento: pd.DataFrame) -> dict:
    """Visão rápida do histórico de atendimento."""
    total = len(atendimento)
    nao_resolvidos = atendimento[atendimento["status"].str.lower() != "resolvido"]

    return {
        "analise": "atendimento_operacional",
        "total_tickets": int(total),
        "nao_resolvidos": int(len(nao_resolvidos)),
        "pct_nao_resolvido": round(len(nao_resolvidos) / total * 100, 1) if total else 0,
    }



# ROTEADOR (mapeia pergunta/ análise)
#============================================================

MAPA_PALAVRAS_CHAVE = {
    "concentracao_receita": ["concentr", "top client", "maior client", "principal client", "depend"],
    "receita_por_categoria": ["categoria", "tipo de servic", "linha de", "o que vend"],
    "receita_por_canal": ["canal", "aquisic", "origem", "indicac", "licitac"],
    "evolucao_mensal": ["mês", "mes ", "mensal", "sazonal", "tendenc", "crescimento", "evolucao", "evolução"],
    "inadimplencia": ["inadimpl", "calote", "estorno", "devolu", "não pagou", "nao pagou", "atraso"],
    "status_metas": ["meta", "objetivo", "alvo", "projecao", "projeção"],
    "atendimento_operacional": ["atendimento", "ticket", "suporte", "operacion"],
}


def rotear(pergunta: str) -> list[str]:
    """Retorna lista de análises relevantes à pergunta. Nunca retorna vazio."""
    p = pergunta.lower()
    analises = [nome for nome, chaves in MAPA_PALAVRAS_CHAVE.items() if any(k in p for k in chaves)]

    # perguntas amplas do tipo "panorama", "resumo", "onde perco dinheiro"
    if any(t in p for t in ["panorama", "resumo", "geral", "onde perco", "onde estou perdendo"]):
        analises = ["concentracao_receita", "inadimplencia", "evolucao_mensal"]

    return analises or ["concentracao_receita"]  # default seguro


def executar_analises(dados: dict, analises: list[str]) -> list[dict]:
    """Executa as análises solicitadas e retorna lista de resultados estruturados."""
    df = dados["transacoes"]
    resultados = []
    despacho = {
        "concentracao_receita": lambda: concentracao_receita(df),
        "receita_por_categoria": lambda: receita_por_categoria(df),
        "receita_por_canal": lambda: receita_por_canal(df),
        "evolucao_mensal": lambda: evolucao_mensal(df),
        "inadimplencia": lambda: inadimplencia(df),
        "status_metas": lambda: status_metas(df, dados["perfil"]),
        "atendimento_operacional": lambda: atendimento_operacional(dados["atendimento"]),
    }
    for a in analises:
        if a in despacho:
            resultados.append(despacho[a]())
    return resultados



# WRAPPER LLM (interpreta)
#============================================================

SYSTEM_PROMPT = """Você é o Atlas, um analista executivo que diagnostica o negócio do empresário com base em dados consolidados pelo banco.

REGRAS CRÍTICAS:
- Use APENAS os números presentes no JSON de análise fornecido. Nunca invente valores.
- Tom: técnico, direto, consultivo. Sem enrolação, sem opinião pessoal.
- Estrutura da resposta: diagnóstico objetivo + 1 a 2 observações estratégicas.
- Se o dado não permitir conclusão forte, declare isso explicitamente.
- Máximo 4 parágrafos curtos.
"""


def resposta_simulada(pergunta: str, resultados: list[dict]) -> str:
    """Gera resposta determinística a partir dos dicts calculados. Usado quando não há API key."""
    partes = [f'**Pergunta:** {pergunta}\n', "**Diagnóstico Atlas:**\n"]

    for r in resultados:
        a = r["analise"]
        if a == "concentracao_receita":
            top = r["top_clientes"]
            partes.append(
                f"- Receita total analisada: R$ {r['receita_total']:,.2f} entre {r['qtd_clientes_ativos']} clientes ativos."
            )
            partes.append(
                f"- Os 3 maiores clientes concentram **{r['pct_top3']}%** da receita: "
                + ", ".join(f"{c['cliente']} ({c['pct']}%)" for c in top)
                + "."
            )
        elif a == "receita_por_categoria":
            principal = r["categorias"][0]
            partes.append(
                f"- Categoria dominante: **{principal['categoria']}** com {principal['pct']}% (R$ {principal['receita']:,.2f})."
            )
        elif a == "receita_por_canal":
            principal = r["canais"][0]
            partes.append(
                f"- Canal mais relevante: **{principal['canal']}** ({principal['pct']}% da receita)."
            )
        elif a == "evolucao_mensal":
            meses = r["meses"]
            if meses:
                primeiro, ultimo = meses[0], meses[-1]
                partes.append(
                    f"- Período analisado: {primeiro['mes']} → {ultimo['mes']}. "
                    f"Média mensal: R$ {r['media_mensal']:,.2f}. "
                    f"Último mês variou **{ultimo['variacao_pct']}%** vs. anterior."
                )
        elif a == "inadimplencia":
            partes.append(
                f"- Inadimplência: {r['eventos']} evento(s) totalizando R$ {r['total_estornos']:,.2f} "
                f"({r['pct_sobre_receita']}% da receita)."
            )
        elif a == "status_metas":
            for m in r["metas"]:
                partes.append(
                    f"- Meta **{m['meta']}**: {m['pct_atingido']}% atingido "
                    f"(R$ {m['valor_atual']:,.2f} de R$ {m['valor_alvo']:,.2f}, prazo {m['prazo']})."
                )
        elif a == "atendimento_operacional":
            partes.append(
                f"- Atendimento: {r['nao_resolvidos']} de {r['total_tickets']} tickets em aberto ({r['pct_nao_resolvido']}%)."
            )

    return "\n".join(partes)


def resposta_llm(pergunta: str, resultados: list[dict]) -> str:
    """Chama a API da Anthropic passando o dict já calculado como contexto."""
    try:
        from anthropic import Anthropic
    except ImportError:
        return resposta_simulada(pergunta, resultados)

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    contexto = json.dumps(resultados, ensure_ascii=False, indent=2)

    msg = client.messages.create(
        model=MODELO_LLM,
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": f"Pergunta do empresário: {pergunta}\n\nResultado das análises (fonte da verdade):\n{contexto}",
        }],
    )
    return msg.content[0].text



# PONTO DE ENTRADA
#============================================================

def responder(pergunta: str, dados: dict | None = None) -> dict:
    """Fluxo completo: roteia -> calcula -> interpreta."""
    if dados is None:
        dados = carregar_dados()

    analises = rotear(pergunta)
    resultados = executar_analises(dados, analises)

    texto = resposta_simulada(pergunta, resultados) if MODO_SIMULADO else resposta_llm(pergunta, resultados)

    return {
        "pergunta": pergunta,
        "analises_executadas": analises,
        "resultados_brutos": resultados,
        "resposta": texto,
    }
#============================================================
#Verificar se a resposta é coerente com os dados, especialmente para perguntas amplas.

if __name__ == "__main__":
    dados = carregar_dados()
    perguntas_teste = [
        "Qual a concentração de receita na minha carteira?",
        "Como está o andamento das metas?",
        "Tenho problema de inadimplência?",
        "Qual canal traz mais receita?",
        "Me dá um panorama geral do negócio.",
    ]
    for p in perguntas_teste:
        out = responder(p, dados)
        print("=" * 70)
        print(out["resposta"])
        print()