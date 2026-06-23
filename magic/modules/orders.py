from collections import namedtuple
from typing import Literal, Any

import MetaTrader5 as mt5
import pandas as pd

from ..helpers.enums import order_map, pos_map, fill_map, time_map, r_pos_map, r_time_map, r_fill_map
from .handlers import BaseHandler
from ..helpers.errors import check_error, get_message


class OrdersHandler(BaseHandler):
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
            "error": data
        }
        
    def success(self, data):
        if hasattr(data, "retcode") and check_error(data.retcode):
            return self.error(data=data)
            
        return super().success(data)

    def total(self):
        return self.res(mt5.orders_total())

    def add(
        self,
        ticker: str,
        type: Literal["market", "limit"],
        direction: Literal["buy", "sell"],
        lot: float,
        price: float | None = None,
        deviation: int | None = None,
        fill_type: Literal["full", "available", "return"] | None = None,
        time_limit: Literal[
            "till_cancelled", "day", "time_specified", "time_specified_day"] | None = None,
        expiration: int | None = None,
        remarks: str | None = None,
        sl: float | None = None,
        tp: float | None = None,
    ):
        """
        Add a New order
        """
        tick = mt5.symbol_info(ticker)
        
        if not tick:
            raise ValueError(f"[{ticker}]: Ticker does not exist. Please check your broker.")

        request = {
            "magic": self.magic,
            "symbol": ticker,
            "action": order_map[type.upper()],
            "type": pos_map[type.upper() + "_" + direction.upper()],
            "volume": lot,
        }

        if type == "limit":
            if not price:
                raise ValueError("Price is required for limit orders")
            if price > tick.ask and price < tick.bid:
                raise ValueError(
                    f"Price {price} is out of range. Current Bid: {tick.bid}, Ask: {tick.ask}"
                )
            if direction == "buy" and price > tick.ask:
                raise ValueError(
                    f"Price {price} is greater than the current Ask price {tick.ask}"
                )
            if direction == "sell" and price < tick.bid:
                raise ValueError(
                    f"Price {price} is less than the current Bid price {tick.bid}"
                )
            else:
                request["price"] = price
                
        if type == "market":
            if direction == "buy":
                request['price'] = mt5.symbol_info_tick(ticker).ask
            if direction == "sell":
                request['price'] = mt5.symbol_info_tick(ticker).bid

        if deviation:
            request["deviation"] = deviation

        if fill_type:
            request["type_filling"] = fill_map[f"{fill_type.upper()}_FILL"]

        if time_limit:
            if (
                time_limit == "time_specified"
                or time_limit == "time_specified_day"
                and not expiration
            ):
                raise ValueError(
                    "Expiration time is required for time specified orders"
                )

            request["type_time"] = time_map[f"VALID_{time_limit.upper()}"]

            if expiration:
                request["expiration"] = expiration

        if remarks:
            request["comment"] = remarks
        else:
            comment = str(self.magic) + ": New Order"
            request["comment"] = comment
            
        if sl:
            if direction == "buy":
                request["sl"] = tick.ask - sl
                
            if direction == "sell":
                request["sl"] = tick.bid + sl
                
        if tp:
            if direction == "buy":
                request["tp"] = tick.ask + tp
                
            if direction == "sell":
                request["tp"] = tick.bid - tp
            
        if self.debug:
            print("\n New Order Request", request)

        result = mt5.order_send(request)
        
        if result:
            result = result._asdict()
            
            # Update Price to be bid/ask price, if MT5 does not provide one
            if(result['price'] == 0):
                result['price'] = request['price']
            
            ModResponse = namedtuple('ModResponse', result) 
            result = ModResponse(**result)

        return self.res(result)

    def modify(self, 
                ticket_id: int, 
                volume: float | None = None, 
                sl: float | None = None, 
                tp: float | None = None):
        """
        Modify an existing order or position
        """
        if not ticket_id:
            raise ValueError("Ticket ID is required to modify an order or position")
        
        order = mt5.orders_get(ticket=ticket_id)
        
        if len(order) == 0:
            raise ValueError(f"Order with ticket id {ticket_id} does not exist. Your order might have been filled & converted to a position.")

    def cancel(self, 
                ticket: int | None = None,
                ticker: str | None = None
        ):
        """
        Cancel any pending orders        
        """
        if not ticket and not ticker:
            raise ValueError("Ticket ID or Ticker are required to cancel an order")
        
        order = None
        if ticket:
            order = mt5.orders_get(ticket=ticket)
        
        if ticker:
            if not mt5.symbol_info(ticker):
                raise ValueError(f"[{ticker}]: Ticker does not exist. Please check your broker.")
            
            order = mt5.orders_get(symbol=ticker)
        
        if not order or len(order) == 0:
            raise ValueError(f"{ticket or ticker}: No orders available to cancel.")
        
        comment = str(ticker or ticket) + ": Order Cancelled"
        
        req = {
            'action': order_map.CANCEL,
            'magic': self.magic,
            'comment': comment
        }
        
        if ticket:
            req["order"] = ticket
        
        if ticker:
            req["symbol"] = ticker
        
        res = mt5.order_send(req)
        
        print(req, res)
        return self.res(res)

    def get(self, 
            ticket: int | None = None, 
            ticker: str | None = None
            ):
        
        req: dict = {}
        
        if ticket:
            req['ticket'] = ticket
            
        if ticker:
            req['symbol'] = ticker
            
        return self.res(mt5.orders_get(**req))
    
    def parse(self, data):
        
        if not data:
            raise Exception("No data available to parse")
        
        orders = []
        for d in data:
            orders.append(
                {
                    "magic": d.magic,
                    "ticket": d.ticket,
                    "symbol": d.symbol,
                    "volume": d.volume_current,
                    "price": d.price_open,
                    "position": d.position_id,
                    "sl": d.sl,
                    "tp": d.tp,
                    "market_price": d.price_current,
                    "initial_volume": d.volume_initial,
                    "type": r_pos_map[d.type],
                    "type_time": r_time_map[d.type_time],
                    "type_filling": r_fill_map[d.type_filling],
                    "comment": d.comment,
                }
            )
        return orders
    
    def pretty(self, data):
        
        
        if type(data) is not list:
            data = [data]
            
        keys = ["Ticket", "Symbol"]
        values = []
        
        for d in data:
            print(d)
            [d.ticket, d.symbol]    
        
        df = pd.DataFrame(values, columns=keys)
        print(df)
        
        # table = [
        #     ["Ticket (Order Id)", data.ticket],
        #     ["Symbol", data.symbol],
        #     ["Volume", data.volume_current],
        #     ["Price", data.price_open],
        #     ["Position", data.position_id],
        #     ["SL", data.sl],
        #     ["TP", data.tp],
        #     ["Market Price", data.price_current],
        #     ["Initial Volume", data.volume_initial],
        #     ["Type", r_pos_map[data.type]],
        #     ["Expiration Type", r_time_map[data.type_time]],
        #     ["Filling Type", r_fill_map[data.type_filling]],
        #     ["Comment", data.comment],
        # ]
        
        # df = pd.DataFrame(table, columns=["Attribute", "Value"])
        
        # print(df)