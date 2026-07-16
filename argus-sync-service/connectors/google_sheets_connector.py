import os
from typing import Any

import requests
from dotenv import load_dotenv


class GoogleSheetsConnector:

    def __init__(self):

        load_dotenv("config/.env")

        self.api_url = os.getenv("LOST_SALES_API_URL")
        self.api_token = os.getenv("LOST_SALES_API_TOKEN")

        if not self.api_url:
            raise ValueError(
                "LOST_SALES_API_URL não foi configurada em config/.env."
            )

        if not self.api_token:
            raise ValueError(
                "LOST_SALES_API_TOKEN não foi configurado em config/.env."
            )

    def fetch_lost_sales(self) -> dict[str, Any]:

        try:
            response = requests.get(
                self.api_url,
                params={"token": self.api_token},
                timeout=45
            )

            response.raise_for_status()
            payload = response.json()

        except requests.RequestException as exc:
            raise RuntimeError(
                f"Falha ao consultar o Google Sheets: {exc}"
            ) from exc

        except ValueError as exc:
            raise RuntimeError(
                "O Apps Script não retornou um JSON válido."
            ) from exc

        if not payload.get("success"):
            error = payload.get("error", "Erro desconhecido")
            raise RuntimeError(
                f"Apps Script retornou erro: {error}"
            )

        data = payload.get("data")

        if not isinstance(data, list):
            raise RuntimeError(
                "O campo 'data' retornado pelo Apps Script não é uma lista."
            )

        return {
            "updated_at": payload.get("updated_at"),
            "total_records": int(payload.get("total_records", len(data))),
            "data": data
        }