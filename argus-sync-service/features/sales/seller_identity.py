import re
import unicodedata


class SellerIdentity:

    PARTICLES = {
        "de",
        "da",
        "do",
        "das",
        "dos",
        "e"
    }

    COMPANY_ALIASES = {
        "NTS RIO DE JANEIRO": "NTS Rio",
        "NTS RIO": "NTS Rio",
        "NTS SAO PAULO": "NTS São Paulo",
        "NTS SÃO PAULO": "NTS São Paulo",
        "NTS BELEM": "NTS Belém",
        "NTS BELÉM": "NTS Belém",
        "CRISTALINA": "Cristalina",
        "DYNAMIC": "Dynamic"
    }

    @staticmethod
    def remove_accents(value):

        if value is None:
            return ""

        value = str(value)

        return "".join(
            c
            for c in unicodedata.normalize("NFKD", value)
            if not unicodedata.combining(c)
        )

    def normalize_name(self, name):

        if name is None:
            return ""

        words = (
            str(name)
            .strip()
            .lower()
            .split()
        )

        formatted = []

        for word in words:

            if word in self.PARTICLES:
                formatted.append(word)

            else:
                formatted.append(word.capitalize())

        return " ".join(formatted)

    def seller_key(self, name):

        normalized = self.remove_accents(name)

        normalized = normalized.lower()

        normalized = re.sub(
            r"[^a-z0-9]+",
            "_",
            normalized
        )

        normalized = normalized.strip("_")

        return normalized

    def display_name(self, name):

        return self.normalize_name(name)

    def normalize_company(self, company):

        if company is None:
            return ""

        company = (
            self.remove_accents(company)
            .upper()
            .strip()
        )

        return self.COMPANY_ALIASES.get(
            company,
            company.title()
        )