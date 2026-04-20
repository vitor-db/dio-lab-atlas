"""
Atlas - Interface Streamlit

Camada fina sobre o agente.py.
"""

import streamlit as st
import pandas as pd
from pathlib import Path

from agente import carregar_dados, responder
from config import MODO_SIMULADO


# CAMINHO DO ÍCONE
#============================================================

project_root = Path(__file__).parent.parent
icon_path = project_root / "assets" / "atlas-brain.svg"


# CONFIGURAÇÃO DA PÁGINA
#============================================================

st.set_page_config(
    page_title="Atlas - Analista Executivo de Dados",   
    page_icon=str(icon_path),
    layout="wide",
)



# CACHE DE DADOS (evita reconciliar a cada interação)
#============================================================

@st.cache_data
def get_dados():
    return carregar_dados()



# SIDEBAR - CONTEXTO DA EMPRESA
#============================================================

dados = get_dados()
perfil = dados["perfil"]

with st.sidebar:
    st.markdown("### 🏢 Empresa Analisada")
    st.markdown(f"**{perfil['razao_social']}**")
    st.caption(f"Segmento: {perfil['segmento']}")

    st.divider()

    if MODO_SIMULADO:
        st.warning("Modo Simulação")
        st.caption("Respostas geradas de forma determinística a partir dos cálculos do pandas. Sem chamada ao LLM.")
    else:
        st.success("LLM conectado")
        st.caption("Respostas interpretadas pelo modelo, com dicts calculados.")

    st.divider()

    st.markdown("### 💡 Sugestões de Pergunta")
    sugestoes = [
        "Qual a concentração de receita na minha carteira?",
        "Como está o andamento das metas?",
        "Tenho problema de inadimplência?",
        "Qual canal traz mais receita?",
        "Como foi a evolução mensal?",
        "Me dá um panorama geral do negócio.",
    ]
    for s in sugestoes:
        if st.button(s, use_container_width=True, key=f"sug_{s}"):
            st.session_state["pergunta_atual"] = s



# CABEÇALHO
#============================================================

col1, col2 = st.columns([0.06, 0.94], gap="small")
with col1:
    st.image(str(icon_path), width=60)
with col2:
    st.title("Atlas")

st.markdown(
    "**Analista executivo:** realiza diagnósticos de negócios com base em dados consolidados da conta bancária."
)
st.caption(
    "Protótipo de estudo — simula um serviço que um banco ofereceria aos seus clientes PJ, "
)

st.divider()



# ENTRADA DA PERGUNTA
#============================================================

pergunta = st.text_input(
    "",
    value=st.session_state.get("pergunta_atual", ""),
    placeholder="Ex: Onde estou concentrando minha receita?",
)

analisar = st.button("Analisar", type="primary")



# RESPOSTA
#============================================================

if analisar and pergunta:
    with st.spinner("Atlas analisando os dados..."):
        resultado = responder(pergunta, dados)

    # Resposta em destaque
    st.markdown("### 🎯 Diagnóstico")
    st.markdown(resultado["resposta"])

    st.divider()

    # Transparência: mostra o que foi calculado por baixo
    with st.expander("🔬 Ver cálculos brutos"):
        st.caption(
            "Estes são os dados calculados em Python antes de qualquer interpretação do LLM. "
            "A transparência é parte da arquitetura anti-alucinação do Atlas."
        )
        st.markdown(f"**Análises executadas:** `{', '.join(resultado['analises_executadas'])}`")
        st.json(resultado["resultados_brutos"])



# RODAPÉ COM CONTEXTO
#============================================================

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Clientes ativos",
        perfil.get("base_clientes_ativa", "—"),
    )
with col2:
    meta_receita = next(
        (m["valor_alvo"] for m in perfil.get("metas", []) if "receita" in m["meta"].lower()),
        None,
    )
    st.metric(
        "Meta de receita anual",
        f"R$ {meta_receita:,.0f}" if meta_receita else "—",
    )
with col3:
    st.metric(
        "Ticket médio declarado",
        f"R$ {perfil.get('ticket_medio_contrato', 0):,.0f}",
    )

st.caption(
    "⚠️ Dados fictícios para fins de estudo. "
    "Os CSVs simulam o retorno do Open Finance + SEFAZ numa arquitetura real."
)