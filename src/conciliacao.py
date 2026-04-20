"""
conciliacao.py
--------------
Cruza o extrato bancário bruto com o mapeamento de clientes
e gera o dado enriquecido usado pela "engine" analítica do Atlas.

Numa implementação real, o extrato viria via Open Finance + SEFAZ. Aqui foi feito via mapeamento do cliente em arquivo CSV."""

import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"


def carregar_dados() -> tuple[pd.DataFrame, pd.DataFrame]:
    extrato = pd.read_csv(DATA_DIR / "extrato_bancario.csv", parse_dates=["data"])
    mapeamento = pd.read_csv(DATA_DIR / "mapeamento_clientes.csv")
    return extrato, mapeamento


def conciliar(extrato: pd.DataFrame, mapeamento: pd.DataFrame) -> pd.DataFrame:
    """
    Cruza extrato bancário com mapeamento de clientes pelo CNPJ.
    Transações de CNPJs não mapeados são marcadas como 'nao_identificado'.
    """
    df = extrato.rename(columns={"cnpj_remetente": "cnpj"}).merge(
        mapeamento[["cnpj", "client_id", "nome_cliente", "categoria", "canal"]],
        on="cnpj",
        how="left"
    )

    df["client_id"] = df["client_id"].fillna("nao_identificado")
    df["nome_cliente"] = df["nome_cliente"].fillna("Não identificado")
    df["categoria"] = df["categoria"].fillna("nao_classificado")
    df["canal"] = df["canal"].fillna("nao_classificado")

    # Tipo derivado do valor: estorno = inadimplencia, positivo = receita
    df["tipo"] = df["valor"].apply(
        lambda v: "inadimplencia" if v < 0 else "receita"
    )

    colunas_finais = [
        "data", "client_id", "nome_cliente", "descricao",
        "categoria", "canal", "modalidade", "valor", "tipo"
    ]

    return df[colunas_finais].sort_values("data").reset_index(drop=True)


def gerar_transacoes_enriquecidas() -> pd.DataFrame:
    """
    Ponto de entrada principal.
    Retorna o DataFrame enriquecido pronto para a engine analítica.
    """
    extrato, mapeamento = carregar_dados()
    transacoes = conciliar(extrato, mapeamento)
    return transacoes


if __name__ == "__main__":
    transacoes = gerar_transacoes_enriquecidas()
    print(f"Transações conciliadas: {len(transacoes)}")
    print(f"Clientes identificados: {transacoes['client_id'].nunique()}")
    print(f"Período: {transacoes['data'].min().date()} → {transacoes['data'].max().date()}")
    print(f"Receita total: R$ {transacoes[transacoes['tipo'] == 'receita']['valor'].sum():,.2f}")
    print("\nAmostra:")
    print(transacoes.head(5).to_string(index=False))