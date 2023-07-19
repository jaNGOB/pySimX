class one_pass:
    def __init__(self) -> None:
        pass

    def update(self):
        pass

    def current_value(self):
        pass


class mean:
    def __init__(self, alpha: float) -> None:
        self.alpha = alpha

        self.ema = None

    def update(self, x_t: float) -> float:
        if self.ema == None:
            self.ema = x_t
        self.ema = (1 - self.alpha) * x_t + self.alpha * self.ema
        return self.ema


class var:
    def __init__(self, alpha: float) -> None:
        self.alpha = alpha
        self.ema = None
        self.var = 1

    def update(self, x_t: float) -> float:
        if self.ema == None:
            self.ema = x_t

        self.var = (1 - self.alpha) * (x_t - self.ema) ** 2 + self.alpha * self.var
        return self.var
