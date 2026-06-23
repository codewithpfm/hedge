import MetaTrader5 as mt5 # type: ignore
from typing import Any

from ..helpers.enums import fill_map
from ..helpers.errors import check_error, get_message

from .handlers import BaseHandler

class PositionHandler(BaseHandler):
    def __init__(self, magic: int = -1, debug: bool = False):
        super().__init__(magic, debug)

    def error(self, data: Any = None, params: Any = None):
        if not data:
            return super().error()

        message = get_message(data.retcode)

        return {
            "magic": self.magic,
            "is_error": True,
            "message": message,
            "data": None,
            "error": data,
        }

    def success(self, data):
        if hasattr(data, "retcode") and check_error(data.retcode):
            return self.error(data=data)
        
        _data = None if len(data) == 0 else data
        return super().success(_data)

    def total(self):
        return self.res(mt5.positions_total())

    def get(self, ticket: int | None = None, ticker: str | None = None):
        req: dict = {}

        if ticket:
            req["ticket"] = ticket

        if ticker:
            req["symbol"] = ticker
            
        positions = mt5.positions_get(**req)
        
        if positions is not None:
            positions = list(map(lambda x: x._asdict(), positions))

        return self.res(positions)

    def modify(self, ticket: int, sl: float, tp: float):
        
        if not ticket: 
            return Exception("Ticket is required to modify a position.")
        
        raise NotImplementedError("positions.modify: Implemetation Needed")
        
        # return self.res(mt5.positions_modify(ticket, sl, tp))

    def exit(self, ticket: int, fill_type: str | None = None):
        
        position = mt5.positions_get(ticket=ticket)
        
        # if not position:
        #     return {
        #         "is_error": False,
        #         "message": "Position does not exist.",
        #         "data": ticket,
        #         "error": None,
        #     }
        
        ticker = position[0].symbol        
        request = {
            'action': mt5.TRADE_ACTION_DEAL,
            'symbol': ticker,
            'position': ticket,
            'type': mt5.ORDER_TYPE_SELL if position[0].type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            'volume': position[0].volume,
            'price': mt5.symbol_info_tick(ticker).bid if position[0].type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(ticker).ask,
            'comment': f"{ticket}: Close Position",
            "deviation": 10,
        }

        if fill_type:
            request["type_filling"] = fill_map[f"{fill_type.upper()}_FILL"]
        
        res = mt5.order_send(**request)       
        return self.res(res)
    
    def parse(self):
        raise NotImplementedError("positions.parse: Implemetation Needed")
    
    def pretty(self):
        raise NotImplementedError("positions.pretty: Implemetation Needed")