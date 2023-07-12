from typing import List, Literal
import numpy as np
from collections import deque
from sortedcontainers import SortedDict
from .matching_engine import OrderBook
from .data_types import TOB, Order, Trade


class Exchange:
    def __init__(self, initial_balance: int = 10_000, fees: List[int] = [0, 2]):
        self.maker_fee = fees[0]
        self.taker_fee = fees[1]
        self.balance = initial_balance

        self.markets = {}

        self.positions = {}
        self.open_orders = {}
        self.trades = SortedDict()

    def top_of_book(self, symbol):
        tb = self.markets[symbol].bp
        ta = self.markets[symbol].ap
        print(f"Bid: {tb} | {ta} :Ask")
        return [tb, ta]

    def _open_orders(self):
        return True if len(self.open_orders) > 0 else False

    def open_position(self, order: Order, timestamp: int):
        """
        Order went through and can be opened on the exchange
        """
        print("Position Opened")
        new_trade = Trade(
            order.order_id,
            order.side,
            1,
            order.amount,
            order.price,
            order.entryTime,
            timestamp,
        )

        order.eventTime = timestamp
        self.balance -= order.amount * order.price + abs(
            order.amount * order.price * self.taker_fee
        )
        self.positions[order.symbol] = order.amount

    def close_position(self, symbol: str, price: float):
        print("Position Closed")
        self.balance += self.positions[symbol] * price - abs(
            self.positions[symbol] * price * self.taker_fee
        )
        self.positions.pop(symbol)


class OHLCExchange(Exchange):
    def __init__(self, initial_balance: int = 10000, fees: List[int] = [0, 2]):
        super().__init__(initial_balance, fees)


class TickExchange(Exchange):
    def __init__(self, initial_balance: int = 10000, fees: List[int] = [0, 2]):
        super().__init__(initial_balance, fees)

        self.orderbook: OrderBook = OrderBook()


class TOB_Exchange(Exchange):
    def __init__(
        self, initial_balance: int = 10000, fees: List[int] = [0, 2], latency=[200, 15]
    ):
        super().__init__(initial_balance, fees)

        self.events = {}
        self.latency = latency
        self.step = 0

    def load_trades(self, symbol: str, trades: List[float]) -> None:
        self.trades[symbol] = trades

    def load_tob(self, tob_updates: List[float], symbol: str) -> None:
        # Initialize a orders queue
        self.open_orders[symbol] = SortedDict()

        # Set initial Orderbook as the start
        tob = tob_updates[0]
        self.markets[symbol] = TOB(
            symbol=symbol, timestamp=tob[0], bq=tob[1], bp=tob[2], ap=tob[3], aq=tob[4]
        )
        # The rest will be taken apart and used as events for the backtester
        # self._process_tob_updates(tob_updates[1:])

        # Open a event queue for the symbol
        self.events = SortedDict()

        # Add all the TOB Updates to the queue
        for i in tob_updates[1:]:
            if i[0] not in self.events.keys():
                self.events[i[0]] = deque()

            self.events[i[0]].append(
                TOB(symbol=symbol, timestamp=i[0], bq=i[1], bp=i[2], ap=i[3], aq=i[4])
            )

    def _process_tob_updates(self, tob_updates):
        pass

    def open(self, symbol: str, amount: float, price: float, side: bool) -> None:
        # Add latency to the timestamp of the last TOB update
        timestamp = self.markets[symbol].timestamp + self.latency

        # If there is already an event in the queue at that time, add it at the end
        if timestamp not in self.events.keys():
            self.events[timestamp] = deque()

        self.events[timestamp].append(Order(symbol, side, amount, price, timestamp))

    def _check_match(self, symbol):
        # If there is a buy order and the price is above the current ask price, we execute it
        while (
            self.markets[symbol].ap <= self.open_orders[symbol].peekitem(0).price
            and self.open_orders[symbol].peekitem(0).side
        ):
            self.open_position()

        # If there is a sell order and the price is lower than the current best bid, we execute it
        while (
            self.markets[symbol].bp >= self.open_orders[symbol].peekitem(0).price
            and not self.open_orders[symbol].peekitem(0).side
        ):
            self.open_position()

    def _simulation_step(self):
        # Select the current event and remove it from the Queue
        event = self.events.peekitem(0)[1].popleft()

        ##############################
        ### Could be done by switch ##
        ##############################

        # If the update is a new TOB, change it
        if type(event) == TOB:
            self.markets[event.symbol] = TOB(
                symbol=event.symbol,
                timestamp=event.timestamp,
                bq=event.bq,
                bp=event.bp,
                ap=event.ap,
                aq=event.aq,
            )
        elif type(event) == Order:
            self.open_orders[event.price] = event

        # Remove the event timestamp if there are no more in the queue at that time
        if len(self.events.peekitem(0)[1]) == 0:
            self.events.popitem(0)

    def run_simulation(self):
        while len(self.events) > 0:
            self._simulation_step()
