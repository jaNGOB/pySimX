import numpy as np
from typing import Optional


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
    def __init__(
        self,
        lookback: int,
        calculate_ema: bool = False,
        calculate_pct_change: bool = False,
    ) -> None:
        """
        Initialize variance calculations.

        :param looback: (int) the maximum historical timewindow that will be taken into account. This value must be based off of the input times (in ms, us, etc.)
        :param calculate_ema: (bool) if this is True, the object will maintain its own EMA calculation, otherwise the EMA value has to be provided in the update.
        :param calculate_pct_change: (bool) if this is True, the object will maintain memory of the last value to calculate percentage changes in values.
        """
        self.lookback = lookback
        self.last_ts = 0
        self.var = 1

        self.calculate_ema = calculate_ema
        self.calculate_pct_change = calculate_pct_change

        if calculate_pct_change:
            self.last_value = 0

        if calculate_ema:
            self.ema = mean(lookback)

    def _update_ema(self, x_t: float, ts: int) -> float:
        current_ema = self.ema.update(x_t, ts)
        return current_ema

    def update(self, x_t: float, ts: int, ema: Optional[float] = None) -> float:
        # if we have to calculate the pct_change, we will do it first and replace x_t by the change.
        if self.calculate_pct_change:
            # quick check if we already have a history. If no, add the current value to history and count it as zero.
            if self.last_value == 0:
                self.last_value = x_t
                x_t = 0
            else:
                tmp = x_t
                x_t = x_t / self.last_value - 1
                self.last_value = tmp

        # if an ema is maintained in this object, update the ema.
        if self.calculate_ema:
            ema = self._update_ema(x_t, ts)

        # finally calculate the weight as the difference in timestamps
        weight = min((ts - self.last_ts) / self.lookback, 1)

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
