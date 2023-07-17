"""
Example from Tardis to download free sample data. First day of the month is available to download without API-Keys.

https://docs.tardis.dev/downloadable-csv-files
"""

# pip install tardis-dev
# requires Python >=3.6
from tardis_dev import datasets
from datetime import datetime

n = datetime.now()
start = f"{n.year}-{n.month:02d}-01"
end = f"{n.year}-{n.month:02d}-02"

datasets.download(
    exchange="binance",
    data_types=[
        # "incremental_book_L2",
        "trades",
        "quotes",
        # "derivative_ticker",
        # "book_snapshot_25",
        # "liquidations",
    ],
    from_date=start,
    to_date=end,
    download_dir="datasets",
    symbols=["COMPBTC"],
    # api_key="YOUR API KEY (optionally)",
)
