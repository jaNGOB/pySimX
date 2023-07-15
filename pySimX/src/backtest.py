from .exchange import OHLCExchange
import pandas as pd


class backtest:
    def __init__(self, ohlc: pd.DataFrame) -> None:
        self.ohlc = ohlc

    def run(self):
        pass
