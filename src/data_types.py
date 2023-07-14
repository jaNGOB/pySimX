from dataclasses import dataclass, field
from itertools import count
from typing import Literal, Optional
from enum import Enum
from collections import OrderedDict


OrderStatus = Enum("OrderStatus", ["open", "filled", "partially_filled"])


# TOB
@dataclass
class TOB:
    symbol: str
    timestamp: int
    bq: float
    bp: float
    ap: float
    aq: float


# Orderbook level
@dataclass
class Level:
    price: float
    size: int = 0
    totalAmount: float = 0
    orders = OrderedDict()


# Order definition
@dataclass
class Order:
    order_id: int = field(default_factory=count().__next__, init=False)
    symbol: str
    side: bool
    taker: bool
    amount: float
    remainingAmount: float = field(init=False)
    price: float
    entryTime: int
    eventTime: Optional[int] = None
    status: OrderStatus = "open"
    parentLevel: Optional[Level] = None

    def __post_init__(self):
        self.remainingAmount = self.amount


# Trade definition
@dataclass
class Trade:
    trade_id: int = field(default_factory=count().__next__, init=False)
    order_id: int
    side: bool
    taker: bool
    amount: float
    price: float
    entryTime: int
    eventTime: int
