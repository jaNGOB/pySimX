class cross_exchange:
    def __init__(self, origin, hedging, initial_quote):
        self.origin = origin
        self.hedging = hedging

        self.base = "BTC"
        self.quote = "USDT"
        self.symbol = self.base + self.quote
        self.amount = 0.01

        self.distance = 100 / 10_000  # place orders at 10bps distance
        self.sensitivity = 20 / 10_000  # after a move of 4bps, replace the order
        self.initial_quote = initial_quote

        self.last_buy_trade = -1
        self.last_sell_trade = -1
        self.timestamp = None

        self.bid_open = None
        self.ask_open = None

        self.sell_open = False
        self.buy_open = False

        self.counter = 0
        self.balances = []

    def run_strategy(self):
        # Update the latest TOBs
        hedging_tob = self.hedging.fetch_tob(self.symbol)
        origin_tob = self.origin.fetch_tob(self.symbol)
        hedging_ask = hedging_tob["ask_price"]
        hedging_bid = hedging_tob["bid_price"]

        self.timestamp = max(origin_tob["timestamp"], hedging_tob["timestamp"])

        skew = abs(self.origin.balances["USDT"] / self.initial_quote)
        self.skew = skew
        distance_up = self.distance * skew

        # If a trade was executed on the origin, make a market order on the hedging exchange
        if len(self.origin.trades) > 0:
            orders = self.origin.orders
            for order in orders:
                if order.status == "filled":
                    if order.side == 1:
                        if self.last_buy_trade < order.order_id:
                            self.last_buy_trade = order.order_id
                            # print("hedging")
                            self.hedging.market_order(
                                self.symbol, self.amount, 0, self.timestamp
                            )
                    else:
                        if self.last_sell_trade < order.order_id:
                            self.last_sell_trade = order.order_id
                            # print("hedging")
                            self.hedging.market_order(
                                self.symbol, self.amount, 1, self.timestamp
                            )

        if len(self.hedging.trades) > 0:
            orders = self.hedging.orders
            for order in orders:
                if order.status == "filled":
                    if order.side == 1:
                        if self.last_sell_trade < order.order_id:
                            self.last_sell_trade = order.order_id
                            self.sell_open = False
                    else:
                        if self.last_buy_trade < order.order_id:
                            self.last_buy_trade = order.order_id
                            self.buy_open = False

        # Open orders if they currently arent open
        if (
            len(self.origin.open_orders[self.symbol][0]) == 0
            and not self.sell_open
            and skew < 0.9
        ):
            new_price = round(hedging_ask * (1 + distance_up * self.distance), 8)
            # print(f"New sell {self.amount} @ {new_price} with {hedging_ask}")
            self.origin.limit_order(
                self.symbol, self.amount, new_price, 0, self.timestamp
            )
            self.ask_open = hedging_ask
            self.sell_open = True

        elif len(self.origin.open_orders[self.symbol][0]) == 1:
            # if the price moved too much, replace the order
            if abs(self.ask_open / hedging_ask - 1) > self.sensitivity:
                new_price = round(hedging_ask * (1 + distance_up * self.distance), 8)
                # print(f"Replacing sell {self.amount} @ {new_price} with {hedging_ask}")
                self.origin.cancel_order(
                    self.origin.open_orders[self.symbol][0].peekitem(0)[1]
                )
                self.origin.limit_order(
                    self.symbol, self.amount, new_price, 0, self.timestamp
                )
                self.ask_open = hedging_ask

        if len(self.origin.open_orders[self.symbol][1]) == 0 and not self.buy_open:
            new_price = round(hedging_ask * (1 - self.distance), 8)
            # print(f"New Buy {self.amount} @ {new_price} with {hedging_bid}")
            self.origin.limit_order(
                self.symbol, self.amount, new_price, 1, self.timestamp
            )
            self.bid_open = hedging_bid
            self.buy_open = True

        # if the price moved too much, replace the order
        elif (abs(self.bid_open / hedging_bid - 1) > self.sensitivity) and (
            len(self.origin.open_orders[self.symbol][1]) == 1
        ):
            new_price = round(hedging_bid * (1 - self.distance), 8)
            # print(f"Replacing buy {self.amount} @ {new_price} with {hedging_bid}")
            self.origin.cancel_order(
                self.origin.open_orders[self.symbol][1].peekitem(0)[1]
            )
            self.origin.limit_order(
                self.symbol, self.amount, new_price, 1, self.timestamp
            )
            self.bid_open = hedging_bid

        # Run the simulation step in the place where we are behind
        if hedging_tob["timestamp"] > origin_tob["timestamp"]:
            self.origin._simulation_step()
        else:
            self.hedging._simulation_step()

    def run_simulation(self):
        while (len(self.origin.events) > 0) and (len(self.hedging.events) > 0):
            self.run_strategy()

            self.counter += 1
            if self.counter >= 100:
                hedging_tob = self.hedging.fetch_tob(self.symbol)
                self.counter = 0
                update = self.origin.balances.copy()
                u_2 = self.hedging.balances.copy()

                update["base_hedging"] = u_2[self.base]
                update["quote_hedging"] = u_2[self.quote]
                update["mid"] = (
                    hedging_tob["bid_price"] + hedging_tob["ask_price"]
                ) / 2

                # print(self.bid_open, hedging_tob['bid_price'], len(origin.open_orders[self.symbol][1]), self.skew, abs(self.bid_open / hedging_tob['bid_price'] - 1) * 10_000)
                update["ts"] = self.timestamp

                self.balances.append(update)
