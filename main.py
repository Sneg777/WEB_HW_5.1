import aiohttp
import asyncio
from datetime import datetime, timedelta
import sys
from typing import List
import json


class HttpError(Exception):
    """Custom exception for HTTP errors."""
    pass


class PrivatBankAPI:
    BASE_URL = "https://api.privatbank.ua/p24api/exchange_rates?json&date="

    async def fetch_exchange_rates(self, session: aiohttp.ClientSession, date: str):
        url = f"{self.BASE_URL}{date}"
        try:
            async with session.get(url) as response:
                if response.status == 200:
                    try:
                        return await response.json()
                    except json.JSONDecodeError:
                        raise HttpError(f"Invalid JSON response for {url}")
                else:
                    raise HttpError(f"Error status: {response.status} for {url}")
        except (aiohttp.ClientConnectorError, aiohttp.InvalidURL) as err:
            raise HttpError(f"Connection error: {url} - {str(err)}")


class ExchangeRateService:
    def __init__(self, api: PrivatBankAPI):
        self.api = api

    async def get_rates(self, days: int, currencies: List[str]):
        if days > 10:
            raise ValueError("Cannot fetch exchange rates for more than 10 days.")

        async with aiohttp.ClientSession() as session:
            tasks = []
            for i in range(days):
                date = (datetime.now() - timedelta(days=i)).strftime("%d.%m.%Y")
                tasks.append(self.api.fetch_exchange_rates(session, date))

            responses = await asyncio.gather(*tasks, return_exceptions=True)

        result = []
        for response in responses:
            if isinstance(response, Exception):
                print(f"Warning: {response}")
                continue
            if response and "date" in response and "exchangeRate" in response:
                date = response["date"]
                rates = {
                    rate["currency"]: {
                        "`sale`": rate.get("saleRate", "N/A"),
                        "purchase": rate.get("purchaseRate", "N/A"),
                    }
                    for rate in response["exchangeRate"]
                    if rate["currency"] in currencies
                }
                result.append({date: rates})
            else:
                print("Warning: Unexpected API response structure.")
        return result


async def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <days>")
        return

    try:
        days = int(sys.argv[1])
        if days > 10:
            print("Error: Cannot fetch exchange rates for more than 10 days.")
            return

        currencies = ["USD", "EUR"]

        api = PrivatBankAPI()
        service = ExchangeRateService(api)

        rates = await service.get_rates(days, currencies)

        print(json.dumps(rates, indent=2, ensure_ascii=False))

    except ValueError as e:
        print(f"Error: {e}")
    except HttpError as e:
        print(f"HTTP Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
