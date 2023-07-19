# pySimX: The Multi-Asset Exchange Simulator
SimX is an event-driven backtester that simulates a multi-asset exchange, including latency simulation and fill strategies. It serves as a platform for testing trading algorithms and strategies under realistic market conditions.

## Features
- **Multi-Asset Simulation**: SimX allows you to trade multiple assets simultaneously, offering a more realistic testing environment for your trading algorithms.
- **Latency Simulation**: The current latency is based on a lognormal distribution on all communications with the exchange (POST and GET)
- **Fill Strategies**: Right now the baseline strategy implemented is a pessimistic filling one with no market impact. While Market orders are crossing the book, the limit orders are only triggered if the oposite side is at the same price or worse. 
- **Three Simulation Modes**: Depending on your access to data, SimX offers multiple modes to accomodate for it. TOB, Orderbook and OHLCV simulator. Currently only TOB is implemented.


## Usage
A few examples are provided: 
- [OB-Imbalance](https://github.com/jaNGOB/pySimX/blob/main/pySimX/examples/tob_imbalance.ipynb): Buy if the top-of-book is dominated by buy pressure and sell if the opposite is true. 
- [Cross-ex arbitrage](https://github.com/jaNGOB/pySimX/blob/main/pySimX/examples/upbit_strat.ipynb): Replicate a book on a second exchange and hedge with a market order after the resting orders are hit on the origin.

## Contributing
We appreciate all contributions.

## License
SimX is open-source software licensed under the MIT license.
