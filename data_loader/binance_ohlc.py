import requests
import pandas as pd
from datetime import datetime


def get_kline(symbol, interval, start):
    # base_url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&startTime={start}&limit=1000"
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&startTime={start}&limit=1000"
    resp = requests.get(url)

    if resp.status_code == 200:
        return resp.json()

    else:
        print(f"encountered error {resp.status_code}")
        print(url)
        return []


def fetch_data(symbol: str, interval: str, start: datetime, end: datetime):
    start = int(datetime.timestamp(start) * 1000)
    end = int(datetime.timestamp(end) * 1000)

    data = []

    while start < end:
        tmp_data = get_kline(symbol, interval, start)

        start = tmp_data[-1][0]

        data += tmp_data

    return data
