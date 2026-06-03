import os

class VaultWriter:

    def __init__(self, vault_path):

        self.vault_path = vault_path

    def sanitize(self, text):

        return text.replace("/", "_")

    def write_company_note(
        self,
        company,
        claims,
        sources,
        related_entities
    ):

        filename = self.sanitize(company)

        path = os.path.join(
            self.vault_path,
            "companies",
            f"{filename}.md"
        )

        lines = []

        lines.append(f"# {company}")
        lines.append("")
        lines.append("## Claims")
        lines.append("")

        for claim in claims:

            lines.append(f"- {claim}")

        lines.append("")
        lines.append("## Sources")
        lines.append("")

        for source in sources:

            lines.append(f"- [[{source}]]")

        lines.append("")
        lines.append("## Related")
        lines.append("")

        for entity in related_entities:

            lines.append(f"- [[{entity}]]")

        with open(path, "w", encoding="utf-8") as f:

            f.write("\n".join(lines))
