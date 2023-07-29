import numpy as np


class one_pass:
    def __init__(self) -> None:
        pass

    def update(self):
        pass

    def current_value(self):
        pass


class mean:
    def __init__(self, lookback_us: int) -> None:
        self.lookback_us = lookback_us
        self.last_ts = 0
        self.ema = None

    def __repr__(self) -> str:
        return self.ema

    def update(self, x_t: float, ts: int) -> float:
        if self.ema == None:
            self.ema = x_t

        weight = min((ts - self.last_ts) / self.lookback_us, 1)

        self.ema = weight * x_t + (1 - weight) * self.ema

        self.last_ts = ts
        return self.ema


class var:
    def __init__(self, lookback_us: int, calculate_ema: bool = False) -> None:
        self.lookback_us = lookback_us
        self.last_ts = 0
        self.var = 1

        self.calculate_ema = calculate_ema

        if calculate_ema:
            self.ema = mean(lookback_us)

    def __repr__(self) -> str:
        return self.var

    def _update_ema(self, x_t: float, ts: int) -> float:
        current_ema = self.ema.update(x_t, ts)
        return current_ema

    def update(self, x_t: float, ts: int, ema: float = None) -> float:
        if self.calculate_ema:
            ema = self._update_ema(x_t, ts)

        weight = min((ts - self.last_ts) / self.lookback_us, 1)

        self.var = weight * (x_t - ema) ** 2 + (1 - weight) * self.var
        self.last_ts = ts
        return self.var


# class lin_reg:
#     def __init__(self, alpha: float) -> None:
#         self.alpha = alpha
#         self.M = np.zeros((2, 2))
#         self.V = np.zeros((2, 1))
#         self.B = 0

#     def update(self, X, Y):
#         self.M = self.alpha * self.M + np.matmul(X.T, X)
#         self.V = self.alpha * self.V + np.matmul(X.T, Y)
#         self.B = np.matmul(np.invert(self.M), self.V)
#         return self.B


class lin_reg:
    def __init__(self) -> None:
        self.alpha = 0
        self.B = 0


class ExpL2Regression:
    # https://osquant.com/papers/recursive-least-squares-linear-regression/#fn:1
    def __init__(self, num_features: int, lam: float, halflife: float):
        self.n = num_features
        self._lambda = lam
        self.beta = np.exp(np.log(0.5) / halflife)
        self.w = np.zeros(self.n)
        self.P = np.diag(np.ones(self.n) * self._lambda)

    def update(self, x: np.ndarray, y: float) -> None:
        r = 1 + (x.T @ self.P @ x) / self.beta
        k = (self.P @ x) / (r * self.beta)
        e = y - x @ self.w
        self.w = self.w + k * e
        k = k.reshape(-1, 1)
        self.P = self.P / self.beta - (k @ k.T) * r

    def predict(self, x: np.ndarray) -> float:
        return self.w @ x
