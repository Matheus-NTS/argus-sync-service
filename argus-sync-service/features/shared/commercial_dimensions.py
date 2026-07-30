import re
import unicodedata

import pandas as pd


class CommercialDimensions:
    """
    Padroniza dimensões comerciais usadas em todo o ARGUS.

    Responsabilidades:
    - normalizar textos;
    - normalizar nomes de empresas;
    - normalizar nomes de vendedores;
    - gerar nomes de exibição;
    - gerar identidade composta do vendedor.

    A identidade oficial do vendedor é sempre:
        Empresa + Vendedor
    """

    COMPANY_MAPPING = {
    "NTS RIO": "NTS Rio",
    "NTS RIO DE JANEIRO": "NTS Rio",
    "NTS RJ": "NTS Rio",

    "NTS SAO PAULO": "NTS Sao Paulo",
    "NTS SP": "NTS Sao Paulo",

    # NOVO
    "ANTS SAO PAULO": "NTS Sao Paulo",

    "NTS BELEM": "NTS Belem",

    "CRISTALINA": "CRISTALINA",
    "DYNAMIC": "DYNAMIC",
}

    SELLER_PARTICLES = {
        "DA",
        "DAS",
        "DE",
        "DO",
        "DOS",
        "E",
    }

    @staticmethod
    def normalize_text(value) -> str:
        """
        Remove acentos, espaços duplicados e converte para caixa alta.

        Exemplo:
            "  NTS São   Paulo " -> "NTS SAO PAULO"
        """
        if pd.isna(value):
            return ""

        normalized = str(value).strip()

        normalized = unicodedata.normalize(
            "NFKD",
            normalized,
        )

        normalized = "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized,
        )

        return normalized.upper()

    @classmethod
    def normalize_company(
        cls,
        value,
    ) -> str:
        """
        Retorna o nome oficial da empresa usado no ARGUS.
        """
        normalized = cls.normalize_text(value)

        if not normalized:
            return "Não informado"

        return cls.COMPANY_MAPPING.get(
            normalized,
            normalized,
        )

    @classmethod
    def normalize_seller(
        cls,
        value,
    ) -> str:
        """
        Retorna a chave interna normalizada do vendedor.
        """
        normalized = cls.normalize_text(value)

        if not normalized:
            return "NAO INFORMADO"

        return normalized

    @classmethod
    def display_seller_name(
        cls,
        value,
    ) -> str:
        """
        Retorna o nome resumido do vendedor para exibição.

        Mantém os dois primeiros nomes significativos e ignora
        partículas como DE, DA, DO, DOS e DAS.

        Exemplos:
            ROMARIO OLIVEIRA DE CARVALHO -> Romario Oliveira
            LEONARDO DE OLIVEIRA DE SOUZA -> Leonardo Oliveira
            JESSICA NATHALIA MENDES COSTA -> Jessica Nathalia
            VALFRIDO -> Valfrido
        """
        normalized = cls.normalize_seller(value)

        if normalized == "NAO INFORMADO":
            return "Não informado"

        meaningful_parts = [
            part
            for part in normalized.split()
            if part not in cls.SELLER_PARTICLES
        ]

        selected_parts = meaningful_parts[:2]

        return " ".join(
            part.capitalize()
            for part in selected_parts
        )

    @classmethod
    def seller_identity(
        cls,
        company,
        seller,
    ) -> str:
        """
        Gera a identidade comercial oficial do vendedor.

        Exemplo:
            NTS Rio::ROMARIO OLIVEIRA DE CARVALHO
        """
        normalized_company = cls.normalize_company(
            company
        )

        normalized_seller = cls.normalize_seller(
            seller
        )

        return (
            normalized_company
            + "::"
            + normalized_seller
        )