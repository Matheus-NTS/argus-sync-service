import pandas as pd

from connectors.sql_server import SQLServerConnector
from extractors.meta_extractor import MetaExtractor


def print_section(title: str) -> None:
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


def normalize_text(series: pd.Series) -> pd.Series:
    return (
        series
        .fillna("")
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace(
            r"\s+",
            " ",
            regex=True,
        )
    )


def normalize_company(series: pd.Series) -> pd.Series:
    normalized = normalize_text(series)

    mapping = {
        "NTS RIO DE JANEIRO": "NTS Rio",
        "NTS RIO": "NTS Rio",
        "NTS SAO PAULO": "NTS Sao Paulo",
        "NTS SÃO PAULO": "NTS Sao Paulo",
        "NTS BELEM": "NTS Belem",
        "NTS BELÉM": "NTS Belem",
        "CRISTALINA": "CRISTALINA",
        "DYNAMIC": "DYNAMIC",
    }

    return normalized.map(
        lambda value: mapping.get(
            value,
            value,
        )
    )


def main():
    connector = SQLServerConnector()

    metas = MetaExtractor(
        connector
    ).extract()

    print_section("BASE ORIGINAL DE METAS")

    print(
        f"Linhas recebidas: {len(metas):,}"
    )

    metas["empresa_normalizada"] = (
        normalize_company(
            metas["Empresa"]
        )
    )

    metas["vendedor_normalizado"] = (
        normalize_text(
            metas["vendedor"]
        )
    )

    metas["ano"] = pd.to_numeric(
        metas["ano"],
        errors="coerce",
    )

    metas["mes"] = pd.to_numeric(
        metas["mes"],
        errors="coerce",
    )

    metas["valor"] = pd.to_numeric(
        metas["valor"],
        errors="coerce",
    )

    invalid_rows = metas[
        metas["ano"].isna()
        | metas["mes"].isna()
        | metas["valor"].isna()
        | (
            metas[
                "empresa_normalizada"
            ] == ""
        )
        | (
            metas[
                "vendedor_normalizado"
            ] == ""
        )
    ].copy()

    print()
    print(
        "Linhas inválidas: "
        f"{len(invalid_rows):,}"
    )

    valid = metas.drop(
        index=invalid_rows.index
    ).copy()

    valid["ano"] = (
        valid["ano"].astype(int)
    )

    valid["mes"] = (
        valid["mes"].astype(int)
    )

    print_section("EMPRESAS NORMALIZADAS")

    company_summary = (
        valid
        .groupby(
            "empresa_normalizada",
            as_index=False,
        )
        .agg(
            linhas=(
                "valor",
                "size",
            ),
            vendedores=(
                "vendedor_normalizado",
                "nunique",
            ),
            meta_total=(
                "valor",
                "sum",
            ),
        )
        .sort_values(
            "empresa_normalizada"
        )
    )

    print(
        company_summary.to_string(
            index=False
        )
    )

    key_columns = [
        "empresa_normalizada",
        "vendedor_normalizado",
        "ano",
        "mes",
    ]

    duplicate_mask = valid.duplicated(
        subset=key_columns,
        keep=False,
    )

    duplicates = valid[
        duplicate_mask
    ].sort_values(
        key_columns
    )

    print_section(
        "DUPLICIDADES NA CHAVE EMPRESA + VENDEDOR + ANO + MÊS"
    )

    print(
        f"Linhas envolvidas em duplicidade: "
        f"{len(duplicates):,}"
    )

    if duplicates.empty:
        print(
            "Nenhuma duplicidade encontrada."
        )
    else:
        print(
            duplicates[
                [
                    "Empresa",
                    "empresa_normalizada",
                    "vendedor",
                    "vendedor_normalizado",
                    "ano",
                    "mes",
                    "valor",
                    "id",
                ]
            ].to_string(
                index=False
            )
        )

        duplicate_summary = (
            duplicates
            .groupby(
                key_columns,
                as_index=False,
            )
            .agg(
                quantidade_linhas=(
                    "valor",
                    "size",
                ),
                meta_somada=(
                    "valor",
                    "sum",
                ),
                meta_minima=(
                    "valor",
                    "min",
                ),
                meta_maxima=(
                    "valor",
                    "max",
                ),
            )
        )

        print()
        print(
            "Resumo das duplicidades:"
        )
        print(
            duplicate_summary.to_string(
                index=False
            )
        )

    print_section("COBERTURA DE METAS")

    coverage = (
        valid
        .groupby(
            [
                "empresa_normalizada",
                "vendedor_normalizado",
                "ano",
            ],
            as_index=False,
        )
        .agg(
            meses_com_meta=(
                "mes",
                "nunique",
            ),
            primeiro_mes=(
                "mes",
                "min",
            ),
            ultimo_mes=(
                "mes",
                "max",
            ),
            meta_anual_cadastrada=(
                "valor",
                "sum",
            ),
        )
        .sort_values(
            [
                "ano",
                "empresa_normalizada",
                "vendedor_normalizado",
            ]
        )
    )

    print(
        coverage.to_string(
            index=False
        )
    )

    incomplete = coverage[
        coverage["meses_com_meta"] < 12
    ]

    print()
    print(
        "Combinações vendedor/ano "
        "com menos de 12 meses de meta: "
        f"{len(incomplete):,}"
    )

    if not incomplete.empty:
        print(
            incomplete.to_string(
                index=False
            )
        )

    print_section("META MENSAL DA EMPRESA")

    company_monthly = (
        valid
        .groupby(
            [
                "ano",
                "mes",
                "empresa_normalizada",
            ],
            as_index=False,
        )
        .agg(
            meta_empresa=(
                "valor",
                "sum",
            ),
            vendedores_com_meta=(
                "vendedor_normalizado",
                "nunique",
            ),
        )
        .sort_values(
            [
                "ano",
                "mes",
                "empresa_normalizada",
            ]
        )
    )

    print(
        company_monthly.to_string(
            index=False
        )
    )

    print_section("META MENSAL GERAL")

    general_monthly = (
        valid
        .groupby(
            [
                "ano",
                "mes",
            ],
            as_index=False,
        )
        .agg(
            meta_geral=(
                "valor",
                "sum",
            ),
            empresas_com_meta=(
                "empresa_normalizada",
                "nunique",
            ),
            vendedores_com_meta=(
                "vendedor_normalizado",
                "nunique",
            ),
        )
        .sort_values(
            [
                "ano",
                "mes",
            ]
        )
    )

    print(
        general_monthly.to_string(
            index=False
        )
    )

    print_section("VALIDAÇÃO FINALIZADA")


if __name__ == "__main__":
    main()