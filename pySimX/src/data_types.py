from dataclasses import dataclass, field
from itertools import count
from typing import Optional
from enum import Enum
from collections import OrderedDict


class OrderStatus(Enum):
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"


ExchangeType = Enum("ExchangeType", ["future", "spot"])


# TOB
@dataclass
class TOB:
    symbol: str
    timestamp: int
    bq: float
    bp: float
    ap: float
    aq: float


# OHLCV
@dataclass
class OHLCV:
    symbol: str
    timestamp: int  # Open Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float


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
    price: Optional[float]
    entryTime: int
    eventTime: Optional[int] = None
    status: OrderStatus = OrderStatus.OPEN
    parentLevel: Optional[Level] = None

    def __post_init__(self):
        self.remainingAmount = self.amount


# Modify Order
@dataclass
class ModifyOrder:
    symbol: str
    order: Order
    new_amount: Optional[float]
    new_price: Optional[float]


@dataclass
class CancelOrder:
    symbol: str
    order: Order


# Trade definition
@dataclass
class Trade:
    symbol: str
    trade_id: int = field(default_factory=count().__next__, init=False)
    order_id: int
    side: bool
    taker: bool
    amount: float
    price: float
    fees: float
    entryTime: int
    eventTime: int
