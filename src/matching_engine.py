from sortedcontainers import SortedDict
from .data_types import Order, Trade, Level, TOB


class TOBMatcher:
    def __init__(self, tob: TOB) -> None:
        self.top_bid = tob.bp
        self.top_ask = tob.ap

    def is_match_possible(self, order: Order):
        if order.side and order.price >= self.top_ask:
            print("executed maker")

        elif not order.side and order.price <= self.top_bid:
            print("executed")


class OrderBook:
    def __init__(self):
        self.bids = SortedDict()
        self.asks = SortedDict()

    def process_match(self, maker: Order, taker: Order):
        # If the taker is bigger than the maker
        if taker.remainingAmount > maker.remainingAmount:
            # Notify maker trade
            maker_trade = Trade(
                maker.order_id,
                maker.side,
                False,
                maker.remainingAmount,
                maker.price,
                maker.entryTime,
                10,
            )
            # Notify Taker Trade
            taker_trade = Trade(
                taker.order_id,
                taker.side,
                True,
                maker.remainingAmount,
                maker.price,
                taker.entryTime,
                10,
            )

            print(f"Trade executed: {maker_trade}")
            print(f"Trade executed: {taker_trade}")

            # Adjust the order size of the taker
            taker.remainingAmount -= maker.remainingAmount
            # And remove the maker
            self.cancel_order(maker)

        # if the taker cannot knock-out the maker
        else:
            # Adjust the amount of the maker
            maker.remainingAmount -= taker.remainingAmount
            # Put the taker to 0. No need to remove since its not added
            taker.remainingAmount = 0
            # If the amounts were exactly equal, we remove the maker
            if maker.remainingAmount == 0:
                self.cancel_order(maker)

    def add_order(self, order: Order) -> None:
        # Define the base tree where the order belongs to and the opposite one
        tree = self.bids if order.side else self.asks
        o_tree = self.asks if order.side else self.bids

        # if we have an open amount, the side is not empty and our order price is more competitive than the tob
        while order.remainingAmount > 0 and o_tree and self.is_match_possible(order):
            # Get the Level information of the top level from the opposite side
            tob = o_tree.peekitem(0)[1] if order.side else o_tree.peekitem(-1)[1]

            # Get order_id and the order of the top level
            matching_order_id, matching_order = next(iter(tob.orders.items()))

            self.process_match(matching_order, order)

        # If the order still has a amount left over, add it to the orderbook
        if order.remainingAmount > 0:
            print(
                f"Adding order {order.order_id}. {order.remainingAmount}@{order.price}"
            )
            # Add a level. Setdefault already checks if it exists or not.
            limit_level = tree.setdefault(order.price, Level(order.price))
            # Add one to the size of how many orders are there and the amount on the level
            limit_level.size += 1
            limit_level.totalAmount += order.remainingAmount
            # Finally we add the order by the order_id to the level
            limit_level.orders[order.order_id] = order
            # the level here is then the limit_level under which the order is
            order.parentLevel = limit_level

    def is_match_possible(self, order: Order):
        # If the order is a bid, check if the price is higher or equal the top ask
        if order.side:
            return order.price >= self.best_ask()
        else:
            return order.price <= self.best_bid()

    def cancel_order(self, order: Order):
        tree = self.bids if order.side else self.asks
        limit_level = tree[order.price]
        del limit_level.orders[order.order_id]
        limit_level.size -= 1
        if limit_level.size == 0:
            del tree[order.price]

    def best_bid(self):
        if self.bids:
            return self.bids.peekitem(-1)[0]
        else:
            return None

    def best_ask(self):
        if self.asks:
            return self.asks.peekitem(0)[0]
        else:
            return None
