"""
Here we define the exchange object. Within it, we have the logic for: 
- Positions & balances
- Open Orders 
- Add, delete, modify orders 
- Execute Orders (Limit and Market)
- Spot (Base, Quote balances)
- Modify Orders
- Delete Orders 

TODO: 
- Add Futures support
- Communication on confirmations, etc. 
"""

from typing import List, Literal, Optional
from collections import deque
from copy import deepcopy
from sortedcontainers import SortedDict
from .matching_engine import OrderBook
from .data_types import (
    OHLCV,
    TOB,
    Order,
    Trade,
    ModifyOrder,
    CancelOrder,
    ExchangeType,
    OrderStatus,
)
from .latency_models import LogNormalLatency, ConstantLatency

# from .analytics import PostTrade


# Setup logging to console
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(name)s - %(exchange_name)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)


class Exchange:
    def __init__(
        self,
        fees: List[int] = [0, 2],
        exchange_type: ExchangeType = "spot",
        name: str = "",
    ) -> None:
        """

        :param fees: (List[int]) a list containing two values for maker and taker
        fees expressed in basispoints.
        :exchange_type: (ExchangeType[Spot, Future])
        :name: (str)
        """
        # Load the fees and transform them from basis-points into percent
        self.maker_fee = fees[0] / 10_000
        self.taker_fee = fees[1] / 10_000

        self.logger = logging.LoggerAdapter(logger, {"exchange_name": name})

        self.balances = {}

        self.markets = {}
        self.market_map = {}

        self.exchange_type = exchange_type
        # If it is a futures / perpetual exchange, we work with the concept of positions
        # So we can add a empty dictionary where we will track open positions
        if exchange_type == "future":
            self.positions = {}

        self.open_orders = {}
        self.trades = []
        self.orders = []

        self.historical_balance = []

    def add_market(self, symbol: str, base: str, quote: str) -> None:
        """
        Adds a new market to the exchange.

        This function simply adds the provided market details to a dictionary
        of market map within the exchange.

        :param symbol: (str) The symbol representing the market, e.g., 'BTC/USD'.
        :param base: (str) The base currency in the market, e.g., 'BTC'.
        :param quote: (str) The quote or counter currency in the market, e.g., 'USD'.
        :param perpetual: (bool)

        :return None:
        """
        self.market_map[symbol] = [base, quote]
        if self.exchange_type == "future":
            self.positions[symbol] = 0

    def add_balance(self, symbol: str, amount: float):
        self.balances[symbol] = amount

    def top_of_book(self, symbol):
        tb = self.markets[symbol].bp
        ta = self.markets[symbol].ap
        logger.info(f"Bid: {tb} | {ta} :Ask")
        return [tb, ta]

    def _update_balance(self, symbol: str) -> None:
        update = self.balances.copy()
        update[symbol + "_mid"] = (
            self.markets[symbol].ap.copy() + self.markets[symbol].bp.copy()
        ) / 2
        update["ts"] = self.markets[symbol].timestamp

        self.historical_balance.append(update)

    def _open_orders(self):
        return True if len(self.open_orders) > 0 else False

    def _adjust_balances_future(self, trade: Trade) -> None:
        self.balances[self.market_map[trade.symbol][1]] += (
            -((trade.side * 2) - 1) * trade.amount * trade.price - trade.fees
        )

        self.positions[trade.symbol] += trade.amount * ((trade.side * 2) - 1)

    def _adjust_balances_spot(self, trade: Trade) -> None:
        """
        We update the base and quote balance in this example of a spot exchange.

        Base update examples. balance += amount * (side * 2 -1).
        Buy 0.1 BTC: balance['BTC'] += 0.1 * (1 * 2 - 1) = 0.1 * 1 = 0.1
        Sell 0.1 BTC: balance['BTC'] += 0.1 * (0 * 2 - 1) = 0.1  * -1 = - 0.1

        Quote update exmples. balance -= amount * price * (side * 2 -1)
        Buy 0.1 BTC @ 30k USD: Balance['USD'] -= 0.1 * 30'000 * (1 * 2 -1) = 3'000 * 1 = 3'000
        Sell 0.1 BTC @ 30k USD: Balance['USD'] -= 0.1 * 30'000 * (0 * 2 -1) = 3'000 * -1 = -3'000
        """
        # Balance update as described above
        self.balances[self.market_map[trade.symbol][0]] += trade.amount * (
            (trade.side * 2) - 1
        )

        # Update the balances
        self.balances[self.market_map[trade.symbol][1]] -= (
            trade.amount * trade.price + trade.fees
        ) * ((trade.side * 2) - 1)

    def open_position(self, order: Order, timestamp: float) -> None:
        """
        Order went through and can be opened it on the exchange.
        We calculate the fees and create a trade. This trade is then sent on
        to open a position on either a spot or futures exchange.

        :param order: (Order)
        :param timestamp: (float)
        """
        order.status = OrderStatus.FILLED
        order.eventTime = timestamp
        order.remainingAmount = order.remainingAmount - order.amount

        # define the fee that will be used for the trade
        fee = self.taker_fee if order.taker else self.maker_fee

        fee_quote = abs(order.amount * order.price * fee)

        # self.positions[order.symbol] = order.amount

        new_trade = Trade(
            symbol=order.symbol,
            order_id=order.order_id,
            side=order.side,
            taker=order.taker,
            amount=order.amount,
            price=order.price,
            fees=fee_quote,
            entryTime=order.entryTime,
            eventTime=timestamp,
        )

        self.logger.info(f"Trade Executed {new_trade}")

        self.trades.append(new_trade)
        self.orders.append(order)

        if self.exchange_type == "spot":
            self._adjust_balances_spot(trade=new_trade)

        if self.exchange_type == "future":
            self._adjust_balances_future(trade=new_trade)

        return new_trade

    # def close_position(self, symbol: str, price: float):
    #     logger.info("Position Closed")
    #     self.balances += self.positions[symbol] * price - abs(
    #         self.positions[symbol] * price * self.taker_fee
    #     )
    #     self.positions.pop(symbol)


class OHLCExchange(Exchange):
    def __init__(
        self,
        fees: List[int] = [0, 2],
        exchange_type: ExchangeType = "spot",
        name: str = "",
    ):
        """
        Initialize the OHLC Exchange.

        :param fees: (List[int]) fees defined as basispoints [maker, taker]
        :param exchange_typ" (ExchangeType)
        """
        super().__init__(fees=fees, exchange_type=exchange_type, name=name)

        self.events = SortedDict()

    def load_ohlcv(self, symbol: str, candles):
        self.logger.info(f"Loading {len(candles)} Candles for {symbol}")
        # Iterate through the trades that need to be added to the events
        for i in candles:
            # make sure the event has a queue at a given timestamp
            i[0] = int(i[0])
            if i[0] not in self.events.keys():
                self.events[i[0]] = deque()

            # once were sure there is a queue, append the trade to the timestamp
            self.events[i[0]].append(
                OHLCV(
                    symbol=symbol,
                    timestamp=i[0],
                    open=i[1],
                    high=i[2],
                    low=i[3],
                    close=i[4],
                    volume=i[5],
                )
            )

        self.logger.info("OHLCV Candles loaded successfully")


class TickExchange(Exchange):
    def __init__(self, initial_balance: int = 10000, fees: List[int] = [0, 2]):
        super().__init__(initial_balance, fees)

        self.orderbook: OrderBook = OrderBook()


class TOB_Exchange(Exchange):
    def __init__(
        self,
        fees: List[int] = [0, 2],
        exchange_type: ExchangeType = "spot",
        latency: LogNormalLatency = LogNormalLatency(mean=5000, sigma=0.3),
        name: str = "",
    ):
        """
        Initialize the TOB Exchange.

        :param fees: (List[int]) fees defined as basispoints [maker, taker]
        :param latency: (List[int]) latency [mean, std] in us

        """
        super().__init__(fees=fees, exchange_type=exchange_type, name=name)

        # Define latency summary metrics
        self.latency = latency

        self.last_timestamp = None

        # Open a event queue for the symbol
        self.events = SortedDict()

    def _add_latency(self, timestamp: float) -> float:
        timestamp += int(self.latency.estimate())
        return timestamp

    def fetch_tob(self, symbol) -> dict[float]:
        update = self.markets[symbol]
        out = {
            "timestamp": self._add_latency(update.timestamp),
            "bid_quantity": update.bq,
            "bid_price": update.bp,
            "ask_price": update.ap,
            "ask_quantity": update.aq,
        }
        return out

    # def overview(self, symbol: str) -> None:
    #     self.logger.info(
    #         f"Bid: {self.markets[symbol].bp:>8} | {self.markets[symbol].ap:>8} :Ask"
    #     )

    #     self.logger.info("Open Buy Orders")
    #     for i in self.open_orders["COMPBTC"][1]:
    #         self.logger.info(f"{i} @ {self.open_orders['COMPBTC'][1][i].amount}")

    #     self.logger.info("Open Sell Orders")
    #     for i in self.open_orders["COMPBTC"][0]:
    #         self.logger.info(f"{i} @ {self.open_orders['COMPBTC'][0][i].amount}")

    def load_trades(self, trades: List[float], symbol: str) -> None:
        self.logger.info(f"Loading {len(trades)} trades for {symbol}")
        # Iterate through the trades that need to be added to the events
        for i in trades:
            # make sure the event has a queue at a given timestamp
            i[0] = int(i[0])
            if i[0] not in self.events.keys():
                self.events[i[0]] = deque()

            side = 1 if i[2] == "buy" else 0

            # once were sure there is a queue, append the trade to the timestamp
            self.events[i[0]].append(
                Trade(
                    symbol=symbol,
                    order_id=-1,
                    side=side,
                    taker=True,
                    amount=i[4],
                    price=i[3],
                    fees=0,
                    entryTime=i[0],
                    eventTime=i[0],
                )
            )

        self.logger.info("Trades loaded successfully")

    def load_tob(self, tob_updates: List[float], symbol: str) -> None:
        self.logger.info(f"Loading {len(tob_updates)} TOB-Updates for {symbol}")
        # Initialize a orders queue
        self.open_orders[symbol] = {}
        self.open_orders[symbol][1] = SortedDict()
        self.open_orders[symbol][0] = SortedDict()

        # Set initial Orderbook as the start
        tob = tob_updates[0]
        self.markets[symbol] = TOB(
            symbol=symbol,
            timestamp=int(tob[0]),
            bq=tob[1],
            bp=tob[2],
            ap=tob[3],
            aq=tob[4],
        )
        # The rest will be taken apart and used as events for the backtester
        # self._process_tob_updates(tob_updates[1:])

        # Add all the TOB Updates to the queue
        for i in tob_updates[1:]:
            i[0] = int(i[0])
            if i[0] not in self.events.keys():
                self.events[i[0]] = deque()

            self.events[i[0]].append(
                TOB(symbol=symbol, timestamp=i[0], bq=i[1], bp=i[2], ap=i[3], aq=i[4])
            )
        self.logger.info("TOB-Updates loaded successfully")

    def market_order(
        self, symbol: str, amount: float, side: bool, local_timestamp: int
    ) -> None:
        """

        :param symbol: (str) Symbol of the traded pair
        :param amount: (float) Amount in base currency that will be traded
        :param side: (bool) 1 if its a buy, 0 if its a sell.

        :return: None
        """
        # Add latency to the timestamp of the last TOB update
        timestamp = self._add_latency(local_timestamp)

        # If there is already an event in the queue at that time, add it at the end
        if timestamp not in self.live_events.keys():
            self.live_events[timestamp] = deque()

        self.live_events[timestamp].append(
            Order(
                symbol=symbol,
                side=side,
                taker=True,
                price=None,
                amount=abs(amount),
                entryTime=local_timestamp,
                eventTime=timestamp,
            )
        )

    def limit_order(
        self, symbol: str, amount: float, price: float, side: bool, local_timestamp: int
    ) -> None:
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
        timestamp = self._add_latency(local_timestamp)

        # If there is already an event in the queue at that time, add it at the end
        if timestamp not in self.live_events.keys():
            self.live_events[timestamp] = deque()

        self.live_events[timestamp].append(
            Order(
                symbol=symbol,
                side=side,
                taker=False,
                amount=abs(amount),
                price=price,
                entryTime=local_timestamp,
                eventTime=timestamp,
            )
        )

    def cancel_order(self, order: Order) -> None:
        """
        Fuction that will cancel an order. The trader has to provide the Order.

        :param order: (Order)

        :return: None
        """
        # Add latency simulation
        timestamp = self._add_latency(self.markets[order.symbol].timestamp)
        if timestamp not in self.live_events.keys():
            self.live_events[timestamp] = deque()

        # Append the CancelOrder
        self.live_events[timestamp].append(
            CancelOrder(symbol=order.symbol, order=order)
        )

    def modify_order(
        self,
        order: Order,
        price: Optional[float] = None,
        amount: Optional[float] = None,
    ) -> None:
        """
        To modify an order, we first open a modification message and assign it.
        Next we check if we received instructions to change the price or amount
        and add the information where necessary
        Finally we add some latency and append it to the events queue.
        """

        new_order = ModifyOrder(symbol=order.symbol, order=order)

        # If there is a change in price, add the information to the new_order
        if price is not None:
            new_order.new_price = price
        # If there are no changes, keep the old price
        else:
            new_order.new_price = order.price

        # If there is a change in amount, add the information to the new_order
        if amount is not None:
            new_order.new_amount = amount

        else:
            new_order.new_amount = order.amount

        timestamp = self._add_latency(self.markets[order.symbol].timestamp)

        # If there is already an event in the queue at that time, add it at the end
        if timestamp not in self.live_events.keys():
            self.live_events[timestamp] = deque()

        self.live_events[timestamp].append(new_order)

    def _check_balance(self, order: Order) -> bool:
        """
        Sanity check that we have enough balance to execute such an order
        before we even place it.
        """
        # If it is a buy, check that we have enough quote currency
        # available to buy the base
        if self.exchange_type == "spot":
            if order.side:
                if (
                    self.balances[self.market_map[order.symbol][1]]
                    < order.amount * order.price
                ):
                    self.logger.warn(
                        f"Buy Order couldnt be opened, not enough balance available \nOpened Amount: {order.amount * order.price}, Available Amount: {self.balances[self.market_map[order.symbol][1]]}"
                    )
                    return False
            # else, check that we have enough base to sell it
            else:
                if self.balances[self.market_map[order.symbol][0]] < order.amount:
                    self.logger.warn(
                        f"Sell Order couldnt be opened, not enough balance available \nOpened Amount: {order.amount}, Available Amount: {self.balances[self.market_map[order.symbol][0]]}"
                    )
                    return False
        elif self.exchange_type == "future":
            if order.side:
                if (
                    self.balances[self.market_map[order.symbol][1]]
                    < order.amount * order.price
                ):
                    self.logger.warn(
                        f"Buy Order couldnt be opened, not enough balance available \nOpened Amount: {order.amount * order.price}, Available Amount: {self.balances[self.market_map[order.symbol][1]]}"
                    )
                    return False

        return True

    def _execute_modification(self, order: ModifyOrder) -> None:
        """
        function that finds the order by the order_id
        and replaces it by the new that is sent.
        The order_id is not updated so we can just look for it directly.

        :param order: (Order)
        """
        orders = self.open_orders[order.symbol][order.side]

        # look for a match and update the new price and amounts
        for o in orders:
            if o.order_id == order.order_id:
                o.price = order.new_price
                o.amount = order.new_amount

    def _execute_cancellation(self, order: CancelOrder, timestamp: float) -> None:
        """
        Actually cancel the order now that was in the queue. Since this order can also
        be executed in the meantime,
        we have to do a try:except.
        """
        try:
            cancelled_order = order.order

            cancelled_order.status = OrderStatus.CANCELLED
            cancelled_order.eventTime = timestamp

            self.open_orders[cancelled_order.symbol][cancelled_order.side].pop(
                cancelled_order.price
            )

            self.orders.append(cancelled_order)

        except Exception as e:
            self.logger.warn(f"Cancellation failed, order {order} not open {e}")

    def _execute_market(self, event: Order, timestamp: float) -> None:
        # We chose the Ask Price if we buy, the Bid Price if we sell
        price = (
            self.markets[event.symbol].ap
            if event.side
            else self.markets[event.symbol].bp
        )

        # Update the price of the Order event
        event.price = price

        # Double check that we have enough balance available to execute the order
        if self._check_balance(event):
            # Open the position if the balance is okay
            self.open_position(order=event, timestamp=timestamp)

    def _check_match_trades(self, trade: Trade, timestamp: float) -> None:
        """
        Function that 'executes' a trade and checks if there is an open order
        of the user which would be hit.

        :param trade: (Trade) trade that the public executed
        :param timestamp: (float) Timestamp

        :return: None
        """
        # if the public trade is a buy and we have an open sell order,
        # go through the sell orders
        # and see if one would have gotten hit by it.
        # public_price >= open_order
        if (trade.side == 1) and len(self.open_orders[trade.symbol][0]) > 0:
            # check the lowest value (0) in our open orders
            # and see if its below the buy order price
            if self.open_orders[trade.symbol][0].peekitem(0)[1].price <= trade.price:
                # We have a match, pop the order out of the open orders
                # and open the position
                order = self.open_orders[trade.symbol][0].popitem(0)[1]
                self.logger.info(f"Trade match found! Order {order} will be opened")
                self.open_position(order=order, timestamp=timestamp)

        # else check if we have a open buy order and the public trade was a sell.
        elif (trade.side == 0) and len(self.open_orders[trade.symbol][1]) > 0:
            # check the last value in the SortedDict (-1) which will be the highest buy
            # price and look for a match
            if self.open_orders[trade.symbol][1].peekitem(-1)[1].price >= trade.price:
                # We have a match, pop the order out of the open orders
                # and open the position
                order = self.open_orders[trade.symbol][1].popitem(-1)[1]
                self.logger.info(f"Trade match found! Order {order} will be opened")
                self.open_position(order=order, timestamp=timestamp)

    def _check_match(self, symbol: str, timestamp: float) -> None:
        # If there is a buy order and the price is above the current ask price,
        # we execute it
        if len(self.open_orders[symbol][1]) > 0:
            while (
                self.markets[symbol].ap
                <= self.open_orders[symbol][1].peekitem(-1)[1].price
            ):
                order = self.open_orders[symbol][1].popitem(0)[1]
                # If the price moved in the meantime which leads to direct execution,
                # it was a taker
                if order.entryTime == timestamp:
                    order.taker = True

                self.open_position(order=order, timestamp=timestamp)

                self.logger.info(f"TOB match found! Order {order} will be opened")

                if len(self.open_orders[symbol][1]) == 0:
                    break

        # If there is a sell order and the price is lower than the current best bid,
        # we execute it
        if len(self.open_orders[symbol][0]) > 0:
            while (
                self.markets[symbol].bp
                >= self.open_orders[symbol][0].peekitem(0)[1].price
            ):
                order = self.open_orders[symbol][0].popitem(-1)[1]
                # If the price moved in the meantime which leads to direct execution,
                # it was a taker
                if order.entryTime == timestamp:
                    order.taker = True

                self.open_position(order=order, timestamp=timestamp)

                self.logger.info(f"TOB match found! Order {order} will be opened")

                if len(self.open_orders[symbol][0]) == 0:
                    break

    def _simulation_step(self) -> None:
        # Select the current event and remove it from the Queue
        ts = self.live_events.peekitem(0)[0]
        event = self.live_events.peekitem(0)[1].popleft()

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
            # If its a market order, execute directly
            if event.taker:
                self._execute_market(event, ts)
            # If its a limit order, put it into the open orders that wait for execution
            else:
                check = self._check_balance(event)
                if check:
                    self.logger.info(f"Order Opened. {event}")
                    self.open_orders[event.symbol][event.side][event.price] = event

        # If the event is a modification, change the order in question.
        elif type(event) == ModifyOrder:
            self._execute_modification(event)

        # If the event is a cancellation, cancel the order
        elif type(event) == CancelOrder:
            self.logger.info(f"Order Cancelled. {event}")
            self._execute_cancellation(event, ts)

        # If the event is a public trade, check if it would lead to execution
        elif type(event) == Trade:
            self._check_match_trades(event, ts)

        # Remove the event timestamp if there are no more in the queue at that time
        if len(self.live_events.peekitem(0)[1]) == 0:
            self.live_events.popitem(0)

        # Finally, check for a match in the current pair
        # event.symbol exists in all possible updates so we can safely call it
        self._check_match(event.symbol, ts)
        self.last_timestamp = ts
        # self.overview(event.symbol)

    # def run_analytics(self):
    #     analytics = PostTrade(self.trades)

    def prepare_backtest(self):
        # self.live_events = self.events.copy()
        self.live_events = deepcopy(self.events)

    def run_simulation(self, strategy, symbol):
        strat = strategy(symbol)
        self.live_events = self.events.copy()
        while len(self.live_events) > 0:
            strat.run_strategy()
            self._simulation_step()
            self._update_balance(symbol)
