from matching_engine import OrderBook
from data_types import Order

# order_id: int, side: bool, amount: float, price: float, entryTime: int
orders = [
    [0, 12.5, 1.01, 1],
    [1, 12.5, 0.99, 1],
    [0, 25, 1.02, 1],
    [1, 25, 0.98, 1],
    [0, 30, 1.01, 2],
    [1, 30, 0.99, 2],
]

o = [Order(*i) for i in orders]

ob = OrderBook()
for order in o:
    ob.add_order(order)
