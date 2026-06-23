import MetaTrader5 as mt5 #type: ignore
import pytz

from .helpers.enums import time_map, fill_map, pos_map, order_map, TF_MAP
from .modules.ticker import Tickers
from .modules.terminal import Terminal
from .modules.orders import OrdersHandler
from .modules.positions import PositionHandler

class Broker:
    TF = TF_MAP
    TIME = time_map
    FILL = fill_map
    POS = pos_map
    ORDER = order_map
    path = "C:/Program Files/Pepperstone MetaTrader 5/terminal64.exe"
    _mt5 = mt5

    def __init__(self, magic_no: int) -> None:
        self.magic = magic_no
        self.tickers = Tickers(magic_no)
        self.terminal = Terminal(magic_no)
        self.orders = OrdersHandler(magic_no)
        self.positions = PositionHandler(magic_no)
        
    def check_tickers(self, tickers):
        for tick in tickers:
            tick_info = mt5.symbol_info(tick)
            
            if tick_info is None:
                raise ValueError(f"Invalid Ticker: {tick}")

    def login(
        self, username: int, password: str, server: str, path: str | None = None
    ) -> None:
        if type(username) is not int:
            raise ValueError("Username must be an integer")

        self.username = username
        self.password = password
        self.server_address = server

        if path is not None:
            self.path = path

    def configure(self, debug: bool = False, tz: pytz.tzinfo = pytz.utc) -> None:
        self.debug = debug
        self.tz = tz

    def connect(self):
        if not self.username:
            raise ValueError("Username not provided")

        if not self.password:
            raise ValueError("Password not provided")

        if not self.server_address:
            raise ValueError("Server address not provided")

        self.connected = mt5.initialize(
            server=self.server_address,
            login=self.username,
            password=self.password,
            path=self.path,
        )

        if not self.connected:
            print(f"Failed to connect to {self.server_address}")
            print(mt5.last_error())

    def get_account(self):
        return mt5.account_info()._asdict()