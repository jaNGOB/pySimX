# pySimX: The Multi-Asset Exchange Simulator
SimX is an event-driven backtester that simulates a multi-asset exchange, including latency simulation and fill strategies. It serves as a platform for testing trading algorithms and strategies under realistic market conditions.

## Features
- **Multi-Asset Simulation**: SimX allows you to trade multiple assets simultaneously, offering a more realistic testing environment for your trading algorithms.
- **Multi-Venue Simulation**: The simulation environment also allows to have active connection to multiple pySimX venues which can be used to trade on multiple venues. 
- **Latency Simulation**: The current latency is based on a lognormal distribution on all communications with the exchange (POST and GET)
- **Fill Strategies**: Right now the baseline strategy implemented is a pessimistic filling one with no market impact. While Market orders are crossing the book, the limit orders are only triggered if the oposite side is at the same price or worse. 
- **Three Simulation Modes**: Depending on your access to data, SimX offers multiple modes to accomodate for it. TOB, Orderbook and OHLCV simulator. Currently only TOB is implemented.


## Usage
To learn more about how this simulator can be used, please visit the documentations [here](https://github.com/jaNGOB/pySimX/tree/main/docs).
A few examples are also provided: 
- [Simple TOB Example](https://github.com/jaNGOB/pySimX/blob/main/pySimX/examples/Simple%20TOB%20Example.ipynb): Buy if the top-of-book is dominated by buy pressure and sell if the opposite is true. 
- [Multi-asset Exmple](https://github.com/jaNGOB/pySimX/blob/main/pySimX/examples/Multi-Asset%20TOB%20Example.ipynb): Example of a simple pairs-trading strategy, simulating multi-leg executions on one exchange.
- [Cross-ex arbitrage](https://github.com/jaNGOB/pySimX/blob/main/pySimX/examples/Cross%20Exchange%20Example.ipynb): Replicate a book on a second exchange and hedge with a market order after the resting orders are hit on the origin.

## Contributing
We appreciate all contributions.

## License
SimX is open-source software licensed under the MIT license.
