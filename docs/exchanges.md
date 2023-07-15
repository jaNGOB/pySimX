# Exchanges 


## TOB Exchange

This exchange implementation takes TOB updates and feeds them into a event queue. This event queue is the heart of the system and consists of all relevant updates that can happen, such as `Trade, Order, Modification, Cancel`. These events are either preloaded or user generated as a reaction to a market environemt. See the picture below for more information.

Possible interractions: 
- `market_order(symbol, amount, side, timestamp)`
- `limit_order(symbol, amount, price, side, timestamp)`
- `cancel_order(order)`
- `fetch_tob(symbol)`

### Prepare Exchange
To prepare the exchange, the TOB events need to be loaded in. The format for this is `[timestamp, bid_amount, bid_price, ask_price, ask_amount]` which can be loaded in through the `load_tob(updates, symbol)` function. 

### Latency Simulation

Currently, latency is simulated using the following approach. We derived the average latency of the TOB updates received as well as the standard deviation. In our pessimistic view, we then draw a lognormal random variable `lognorm(0, stdev)` which is then multiplied with the average latency. 

This latency is added to the timestamp on orders and cancels that enter the system, as well as top-of-book updates that exit it. 

![latency_example](https://github.com/jaNGOB/pySimX/blob/main/docs/pictures/latency.png)

### Fills
Right now, an order is filled when the opposite top-of-book is equal or worse than the order price. 

### Example
In the imbalance example 



## TODO: 
- Add public Trades to events