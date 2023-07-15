# Exchanges 


## TOB Exchange

This exchange implementation takes TOB updates and feeds them into a event queue. 


Possible interractions: 
- `market_order(symbol, amount, side, timestamp)`
- `limit_order(symbol, amount, price, side, timestamp)`
- `cancel_order(order)`
- `fetch_tob(symbol)`


### Latency Simulation

Currently, latency is simulated using the following approach. We derived the average latency of the TOB updates received as well as the standard deviation. In our pessimistic view, we then draw a lognormal random variable `lognorm(0, stdev)` which is then multiplied with the average latency. 

This latency is added to the timestamp on orders and cancels that enter the system, as well as top-of-book updates that exit it. 

### Fills
Right now, an order is filled when the opposite top-of-book is equal or worse than the order price. 



## TODO: 
- Add public Trades to events