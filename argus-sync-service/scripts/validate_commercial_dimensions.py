from features.shared.commercial_dimensions import (
    CommercialDimensions,
)


def print_section(title: str) -> None:
    print()
    print("=" * 90)
    print(title)
    print("=" * 90)


def main():
    print_section("NORMALIZAÇÃO DE EMPRESAS")

    company_cases = [
        "NTS Rio",
        "NTS Rio de Janeiro",
        "nts rio",
        "NTS São Paulo",
        "NTS Sao Paulo",
        "NTS SP",
        "NTS Belém",
        "CRISTALINA",
    ]

    for company in company_cases:
        normalized = (
            CommercialDimensions.normalize_company(
                company
            )
        )

        print(
            f"{company!r:30} -> {normalized!r}"
        )

    print_section("PADRONIZAÇÃO DE VENDEDORES")

    seller_cases = [
        "ROMARIO OLIVEIRA DE CARVALHO",
        "Leonardo de Oliveira de Souza",
        "  JESSICA   NATHALIA MENDES COSTA ",
        "VALFRIDO",
        "Débolyn Taísa Queiroz Cardoso",
    ]

    for seller in seller_cases:
        key = (
            CommercialDimensions.normalize_seller(
                seller
            )
        )

        display = (
            CommercialDimensions.display_seller_name(
                seller
            )
        )

        print(
            f"Original: {seller!r}"
        )
        print(
            f"Chave:    {key!r}"
        )
        print(
            f"Exibição: {display!r}"
        )
        print("-" * 90)

    print_section("IDENTIDADE COMPOSTA")

    identities = [
        (
            "NTS Rio",
            "ROMARIO OLIVEIRA DE CARVALHO",
        ),
        (
            "NTS São Paulo",
            "ROMARIO OLIVEIRA DE CARVALHO",
        ),
        (
            "NTS Belém",
            "JESSICA NATHALIA MENDES COSTA",
        ),
    ]

    for company, seller in identities:
        identity = (
            CommercialDimensions.seller_identity(
                company=company,
                seller=seller,
            )
        )

        print(identity)

    print_section("VALIDAÇÃO FINALIZADA")


if __name__ == "__main__":
    main()