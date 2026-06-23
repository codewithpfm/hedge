from config import HARD_STOP_LOSS_PERCENT, STOP_LOSS_MULTIPLIER, TAKE_PROFIT_MULTIPLIER


class PositionState:
    def __init__(self):
        self.in_position = False
        self.direction = None
        self.entry_price = None
        self.entry_time = None
        self.hard_sl_price = None
        self.dynamic_sl_price = None
        self.tp_price = None
        self.mt5_ticket = None
        self.lot_size = None

    def enter(self, direction, price, sl_pct, tp_pct, ticket, dt, lot_size=None):
        self.in_position = True
        self.direction = direction
        self.entry_price = price
        self.entry_time = dt
        self.mt5_ticket = ticket
        self.lot_size = lot_size

        if direction == "long":
            self.hard_sl_price = price * (1 - HARD_STOP_LOSS_PERCENT)
            self.dynamic_sl_price = price * (1 - abs(sl_pct) * STOP_LOSS_MULTIPLIER)
            self.tp_price = price * (1 + abs(tp_pct) * TAKE_PROFIT_MULTIPLIER)
        else:
            self.hard_sl_price = price * (1 + HARD_STOP_LOSS_PERCENT)
            self.dynamic_sl_price = price * (1 + abs(sl_pct) * STOP_LOSS_MULTIPLIER)
            self.tp_price = price * (1 - abs(tp_pct) * TAKE_PROFIT_MULTIPLIER)

    def reset(self):
        self.__init__()

    def __repr__(self):
        if not self.in_position:
            return "PositionState(flat)"
        return (
            f"PositionState({self.direction} @ {self.entry_price:.5f} | "
            f"SL: {self.dynamic_sl_price:.5f} | TP: {self.tp_price:.5f} | "
            f"ticket: {self.mt5_ticket})"
        )
