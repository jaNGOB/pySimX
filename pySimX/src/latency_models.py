import numpy as np


class Latency:
    def __init__(self) -> None:
        pass

    def estimate(self) -> float:
        pass


class ConstantLatency(Latency):
    def __init__(self, latency: float) -> None:
        super().__init__()
        self.latency = latency

    def estimate(self) -> float:
        return self.latency


class LogNormalLatency(Latency):
    def __init__(self, mean, sigma) -> None:
        super().__init__()

        self.mean = mean
        self.sigma = sigma

    def estimate(self) -> float:
        return np.random.lognormal(0, self.sigma, 1)[0] * self.mean
