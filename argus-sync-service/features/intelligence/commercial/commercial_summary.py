class CommercialSummary:

    def build(self, facts):

        if not facts:
            return "Ainda não há fatos comerciais suficientes para gerar um resumo executivo."

        descriptions = [
            fact["description"]
            for fact in facts
        ]

        summary = " ".join(descriptions)

        return summary