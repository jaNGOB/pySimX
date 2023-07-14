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

    def open_position(self, order: Order, timestamp: int) -> None:
        """
        Order went through and can be opened on the exchange
        """
        new_trade = Trade(
            order.order_id,
            order.side,
            order.taker,
            order.amount,
            order.price,
            order.entryTime,
            timestamp,
        )
        print("Position Opened", new_trade)

        order.eventTime = timestamp
        self.balance -= order.amount * order.price + abs(
            order.amount * order.price * self.taker_fee
        )
        self.positions[order.symbol] = order.amount

        self.trades[timestamp] = new_trade

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
        self.latency_mean = latency[0]
        self.latency_dev = latency[1]

    def overview(self, symbol: str) -> None:
        print(f"Bid: {self.markets[symbol].bp:>8} | {self.markets[symbol].ap:>8} :Ask")

        print("Open Buy Orders")
        for i in self.open_orders["COMPBTC"][1]:
            print(f"{i} @ {self.open_orders['COMPBTC'][1][i].amount}")

        print("Open Sell Orders")
        for i in self.open_orders["COMPBTC"][0]:
            print(f"{i} @ {self.open_orders['COMPBTC'][0][i].amount}")

    def load_trades(self, symbol: str, trades: List[float]) -> None:
        self.trades[symbol] = trades

    def load_tob(self, tob_updates: List[float], symbol: str) -> None:
        # Initialize a orders queue
        self.open_orders[symbol] = {}
        self.open_orders[symbol][1] = SortedDict()
        self.open_orders[symbol][0] = SortedDict()

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

    def market_order(self, symbol: str, amount: float, side: bool) -> None:
        price = self.markets[symbol].ap if side else self.markets[symbol].bp

    def limit_order(self, symbol: str, amount: float, price: float, side: bool) -> None:
        """
        Function that adds an order to the events queue. First there is some added
        Latency that can be defined in the initiation of the exchange object itself.
        Then we add it to the queue of the relevant timestamp or open a new queue if we
        dont have a step yet at that time.

        :param symbol: (str) Symbol of the traded pair
        :param amount: (float) Amount in base currency that will be traded
        :param price: (float) Price of the order.
        :param side: (bool) 1 if its a buy, 0 if its a sell.

        :return: None
        """
        # Add latency to the timestamp of the last TOB update
        timestamp = (
            self.markets[symbol].timestamp
            + np.random.lognormal(0, self.latency_dev, 1) * self.latency_mean
        )

        # If there is already an event in the queue at that time, add it at the end
        if timestamp not in self.events.keys():
            self.events[timestamp] = deque()

        self.events[timestamp].append(
            Order(symbol, side, False, amount, price, timestamp)
        )

    def _check_match(self, symbol: str, timestamp: int):
        # If there is a buy order and the price is above the current ask price, we execute it
        if len(self.open_orders[symbol][1]) > 0:
            while (
                self.markets[symbol].ap
                <= self.open_orders[symbol][1].peekitem(-1)[1].price
            ):
                order = self.open_orders[symbol][1].popitem(0)
                self.open_position(order=order[1], timestamp=timestamp)

                if len(self.open_orders[symbol][1]) == 0:
                    break

        # If there is a sell order and the price is lower than the current best bid, we execute it
        if len(self.open_orders[symbol][0]) > 0:
            while (
                self.markets[symbol].bp
                >= self.open_orders[symbol][0].peekitem(0)[1].price
            ):
                order = self.open_orders[symbol][0].popitem(-1)
                self.open_position(order=order[1], timestamp=timestamp)

                if len(self.open_orders[symbol][0]) == 0:
                    break

    def _simulation_step(self):
        # Select the current event and remove it from the Queue
        ts = self.events.peekitem(0)[0]
        event = self.events.peekitem(0)[1].popleft()

        ##############################
        ### Could be done by switch ##
        ##############################

        # If the update is a new TOB, change it
        if type(event) == TOB:
            self.markets[event.symbol] = TOB(
                symbol=event.symbol,
                timestamp=ts,
                bq=event.bq,
                bp=event.bp,
                ap=event.ap,
                aq=event.aq,
            )
        # If the update is an order, execute the order
        elif type(event) == Order:
            self.open_orders[event.symbol][event.side][event.price] = event

        # Remove the event timestamp if there are no more in the queue at that time
        if len(self.events.peekitem(0)[1]) == 0:
            self.events.popitem(0)

        # Finally, check for a match in the current pair
        # event.symbol exists in all possible updates so we can safely call it
        self._check_match(event.symbol, ts)
        self.overview(event.symbol)

    def run_simulation(self, strategy):
        while len(self.events) > 0:
            strategy(self.markets, self.open_orders, self.balance)
            self._simulation_step()
