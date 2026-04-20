"""
config.py
---------
Configurações principais do Atlas.
As variáveis sensíveis são carregadas via .env para facilitar o desenvolvimento local e a implantação.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Diretórios
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"

# LLM
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODELO_LLM = "claude-sonnet-4-20250514"
LLM_MAX_TOKENS = 1024

# Modo simulado — True se não houver chave configurada
MODO_SIMULADO = not bool(ANTHROPIC_API_KEY)

# Arquivos de dados
EXTRATO_PATH = DATA_DIR / "extrato_bancario.csv"
MAPEAMENTO_PATH = DATA_DIR / "mapeamento_clientes.csv"
PERFIL_PATH = DATA_DIR / "perfil_empresa.json"
PRODUTOS_PATH = DATA_DIR / "produtos_financeiros.json"
ATENDIMENTO_PATH = DATA_DIR / "historico_atendimento.csv"