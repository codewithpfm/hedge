import MetaTrader5 as mt5
from .handlers import BaseHandler

class Terminal(BaseHandler):
    
    def __init__(self, magic: int = -1, debug: bool = False):
        super().__init__(magic, debug)
    
    def version(self):
        return self.res(mt5.version())

    def info(self):
        return self.res(mt5.terminal_info()._asdict())