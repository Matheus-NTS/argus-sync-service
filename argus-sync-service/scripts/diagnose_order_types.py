from pathlib import Path
import sys
import unicodedata

import pandas as pd
from sqlalchemy import text


# Permite importar módulos da raiz quando o script é executado por:
# python scripts\diagnose_order_types.py
PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from connectors.sql_server import SQLServerConnector


def normalize_column_name(value: str) -> str:
    value = str(value).strip().lower()

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = value.replace(" ", "_")
    value = value.replace("-", "_")
    value = value.replace("/", "_")

    return value


def normalize_text(series: pd.Series) -> pd.Series:
    return (
        series
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
    )


def find_column(
    dataframe: pd.DataFrame,
    candidates: list[str],
) -> str | None:
    for candidate in candidates:
        if candidate in dataframe.columns:
            return candidate

    return None


def convert_numeric(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_numeric(series, errors="coerce").fillna(0)

    cleaned = (
        series
        .fillna("0")
        .astype(str)
        .str.strip()
        .str.replace("R$", "", regex=False)
        .str.replace(" ", "", regex=False)
    )

    # Formato brasileiro: 1.234,56
    brazilian_mask = (
        cleaned.str.contains(",", regex=False)
        & cleaned.str.contains(".", regex=False)
    )

    cleaned.loc[brazilian_mask] = (
        cleaned.loc[brazilian_mask]
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )

    # Valores somente com vírgula: 1234,56
    comma_mask = (
        cleaned.str.contains(",", regex=False)
        & ~cleaned.str.contains(".", regex=False)
    )

    cleaned.loc[comma_mask] = (
        cleaned.loc[comma_mask]
        .str.replace(",", ".", regex=False)
    )

    return pd.to_numeric(
        cleaned,
        errors="coerce",
    ).fillna(0)


def main():
    print("=" * 80)
    print("DIAGNÓSTICO DE TIPOS DE PEDIDO — ARGUS")
    print("=" * 80)

    connector = SQLServerConnector()

    print("\nConectando ao SQL Server...")

    query = text(
        """
        SELECT *
        FROM dbo.agrc_pedido_lucas
        """
    )

    pedidos = pd.read_sql(
        query,
        connector.engine,
    )

    print(f"Registros extraídos: {len(pedidos):,}")

    original_columns = list(pedidos.columns)

    pedidos.columns = [
        normalize_column_name(column)
        for column in pedidos.columns
    ]

    print("\nColunas encontradas na origem:")

    for original, normalized in zip(
        original_columns,
        pedidos.columns,
    ):
        print(f"  {original} -> {normalized}")

    situacao_column = find_column(
        pedidos,
        [
            "situacao",
            "status",
            "situacao_pedido",
            "status_pedido",
        ],
    )

    tipo_pedido_column = find_column(
        pedidos,
        [
            "tipo_pedido",
            "tipopedido",
            "tipo",
            "tipo_de_pedido",
        ],
    )

    revenue_column = find_column(
        pedidos,
        [
            "valor_total",
            "total",
            "valor",
            "faturamento",
            "vlr_total",
            "valor_pedido",
            "total_pedido",
        ],
    )

    order_column = find_column(
        pedidos,
        [
            "pedido",
            "numero_pedido",
            "num_pedido",
            "codigo_pedido",
            "id_pedido",
            "id",
        ],
    )

    seller_column = find_column(
        pedidos,
        [
            "vendedor",
            "nome_vendedor",
            "representante",
            "consultor",
        ],
    )

    date_column = find_column(
        pedidos,
        [
            "data",
            "data_pedido",
            "data_emissao",
            "emissao",
            "dt_pedido",
        ],
    )

    print("\nColunas utilizadas no diagnóstico:")
    print(f"  Situação: {situacao_column}")
    print(f"  Tipo de pedido: {tipo_pedido_column}")
    print(f"  Faturamento: {revenue_column}")
    print(f"  Número do pedido: {order_column}")
    print(f"  Vendedor: {seller_column}")
    print(f"  Data: {date_column}")

    if situacao_column is None:
        raise KeyError(
            "Não foi possível localizar a coluna de situação."
        )

    if tipo_pedido_column is None:
        raise KeyError(
            "Não foi possível localizar a coluna tipo_pedido."
        )

    pedidos["_situacao_normalizada"] = normalize_text(
        pedidos[situacao_column]
    )

    pedidos["_tipo_pedido_normalizado"] = normalize_text(
        pedidos[tipo_pedido_column]
    )

    concretizados = pedidos[
        pedidos["_situacao_normalizada"] == "CONCRETIZADO"
    ].copy()

    print("\n" + "-" * 80)
    print("FILTRO OBRIGATÓRIO")
    print("-" * 80)
    print(
        "Registros com situação CONCRETIZADO: "
        f"{len(concretizados):,}"
    )

    if revenue_column:
        concretizados["_faturamento"] = convert_numeric(
            concretizados[revenue_column]
        )
    else:
        concretizados["_faturamento"] = 0.0

    if date_column:
        concretizados["_data_diagnostico"] = pd.to_datetime(
            concretizados[date_column],
            errors="coerce",
            dayfirst=True,
        )

    aggregation = {
        "linhas": (
            "_tipo_pedido_normalizado",
            "size",
        ),
        "faturamento": (
            "_faturamento",
            "sum",
        ),
    }

    if order_column:
        aggregation["pedidos_distintos"] = (
            order_column,
            "nunique",
        )

    if seller_column:
        aggregation["vendedores_distintos"] = (
            seller_column,
            "nunique",
        )

    if date_column:
        aggregation["primeira_data"] = (
            "_data_diagnostico",
            "min",
        )
        aggregation["ultima_data"] = (
            "_data_diagnostico",
            "max",
        )

    diagnostico = (
        concretizados
        .groupby(
            "_tipo_pedido_normalizado",
            dropna=False,
        )
        .agg(**aggregation)
        .reset_index()
        .rename(
            columns={
                "_tipo_pedido_normalizado": "tipo_pedido",
            }
        )
        .sort_values(
            by="faturamento",
            ascending=False,
        )
    )

    print("\n" + "=" * 80)
    print("TIPOS DE PEDIDO COM SITUAÇÃO CONCRETIZADO")
    print("=" * 80)

    with pd.option_context(
        "display.max_rows",
        None,
        "display.max_columns",
        None,
        "display.width",
        220,
        "display.float_format",
        lambda value: f"{value:,.2f}",
    ):
        print(diagnostico.to_string(index=False))

    output_directory = PROJECT_ROOT / "logs"
    output_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_directory
        / "diagnostico_tipo_pedido.csv"
    )

    diagnostico.to_csv(
        output_path,
        index=False,
        sep=";",
        encoding="utf-8-sig",
        decimal=",",
    )

    print("\n" + "=" * 80)
    print("DIAGNÓSTICO CONCLUÍDO")
    print("=" * 80)
    print(f"Arquivo salvo em: {output_path}")


if __name__ == "__main__":
    main()