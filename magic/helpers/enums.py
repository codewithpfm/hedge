import MetaTrader5 as mt5
from .utils import Map, reverse_dict

TF_MAP = {
    "1M": mt5.TIMEFRAME_M1,
    "2M": mt5.TIMEFRAME_M2,
    "3M": mt5.TIMEFRAME_M3,
    "4M": mt5.TIMEFRAME_M4,
    "5M": mt5.TIMEFRAME_M5,
    "6M": mt5.TIMEFRAME_M6,
    "10M": mt5.TIMEFRAME_M10,
    "12M": mt5.TIMEFRAME_M12,
    "15M": mt5.TIMEFRAME_M15,
    "30M": mt5.TIMEFRAME_M30,
    "1H": mt5.TIMEFRAME_H1,
    "2H": mt5.TIMEFRAME_H2,
    "3H": mt5.TIMEFRAME_H3,
    "4H": mt5.TIMEFRAME_H4,
    "6H": mt5.TIMEFRAME_H6,
    "8H": mt5.TIMEFRAME_H8,
    "12H": mt5.TIMEFRAME_H12,
    "1D": mt5.TIMEFRAME_D1,
    "1W": mt5.TIMEFRAME_W1,
    "1MN": mt5.TIMEFRAME_MN1,
}

TF_MINUTES_MAP = {
    "1M": 1,
    "2M": 2,
    "3M": 3,
    "4M": 4,
    "5M": 5,
    "6M": 6,
    "7M": 7,
    "8M": 8,
    "9M": 9,
    "10M": 10,
    "11M": 11,
    "12M": 12,
    "13M": 13,
    "14M": 14,
    "15M": 15,
    "16M": 16,
    "17M": 17,
    "18M": 18,
    "19M": 19,
    "20M": 20,
    "21M": 21,
    "22M": 22,
    "23M": 23,
    "24M": 24,
    "25M": 25,
    "26M": 26,
    "27M": 27,
    "28M": 28,
    "29M": 29,
    "30M": 30,
    "31M": 31,
    "32M": 32,
    "33M": 33,
    "34M": 34,
    "35M": 35,
    "36M": 36,
    "37M": 37,
    "38M": 38,
    "39M": 39,
    "40M": 40,
    "41M": 41,
    "42M": 42,
    "43M": 43,
    "44M": 44,
    "45M": 45,
    "46M": 46,
    "47M": 47,
    "48M": 48,
    "49M": 49,
    "50M": 50,
    "51M": 51,
    "52M": 52,
    "53M": 53,
    "54M": 54,
    "55M": 55,
    "56M": 56,
    "57M": 57,
    "58M": 58,
    "59M": 59,
    "1H": 60,
}


ORDER_TYPES_MAP = {
    # Immediate Execution w/ specified parameters (market order)
    "MARKET": mt5.TRADE_ACTION_DEAL,
    # Order with conditions (pending order)
    "LIMIT": mt5.TRADE_ACTION_PENDING,
    # Modify Stoploss & Take Profit values for opened order
    "STOP": mt5.TRADE_ACTION_SLTP,
    # Modify parameters of previously placed order
    "MODIFY": mt5.TRADE_ACTION_MODIFY,
    # delete pending order
    "CANCEL": mt5.TRADE_ACTION_REMOVE,
    # square off an opened position, (close opened order by opposite one)
    "EXIT": mt5.TRADE_ACTION_CLOSE_BY,
}

POSIION_TYPE_MAP = {
    "MARKET_BUY": mt5.ORDER_TYPE_BUY,
    "MARKET_SELL": mt5.ORDER_TYPE_SELL,
    "LIMIT_BUY": mt5.ORDER_TYPE_BUY_LIMIT,
    "LIMIT_SELL": mt5.ORDER_TYPE_SELL_LIMIT,
    "LIMIT_BUY_STOP": mt5.ORDER_TYPE_BUY_STOP,
    "LIMIT_SELL_STOP": mt5.ORDER_TYPE_SELL_STOP,
    "LIMIT_BUY_STOP_LIMIT": mt5.ORDER_TYPE_BUY_STOP_LIMIT,
    "LIMIT_SELL_STOP_LIMIT": mt5.ORDER_TYPE_SELL_STOP_LIMIT,
    "EXIT": mt5.ORDER_TYPE_CLOSE_BY,
}

FILLING_TYPE_MAP = {
    "FULL_FILL": mt5.ORDER_FILLING_FOK,
    "AVAILABLE_FILL": mt5.ORDER_FILLING_IOC,
    "RETURN_FILL": mt5.ORDER_FILLING_RETURN,
}

TIME_TYPE_MAP = {
    # order stays in the queue until it is manually canceled
    "VALID_TILL_CANCELED": mt5.ORDER_TIME_GTC,
    # order is active only during the current trading day
    "VALID_DAY": mt5.ORDER_TIME_DAY,
    # order is active until the specified date
    "VALID_TIME_SPECIFIED": mt5.ORDER_TIME_SPECIFIED,
    # order is active until 23:59:59 of the specified day. If this time appears to be out of a trading session, the expiration is processed at the nearest trading time.
    "VALID_TIME_SPECIFIED_DAY": mt5.ORDER_TIME_SPECIFIED_DAY,
}

order_map = Map(ORDER_TYPES_MAP)
pos_map = Map(POSIION_TYPE_MAP)
fill_map = Map(FILLING_TYPE_MAP)
time_map = Map(TIME_TYPE_MAP)

r_tf_map = reverse_dict(TIME_TYPE_MAP)
r_order_map = reverse_dict(ORDER_TYPES_MAP)
r_pos_map = reverse_dict(POSIION_TYPE_MAP)
r_fill_map = reverse_dict(FILLING_TYPE_MAP)
r_time_map = reverse_dict(TIME_TYPE_MAP)

# r_order_maps = {
#     mt5.TRADE_ACTION_DEAL: "market",
#     mt5.TRADE_ACTION_PENDING: "limit",
#     mt5.TRADE_ACTION_SLTP: "stop",
#     mt5.TRADE_ACTION_MODIFY: "modify",
#     mt5.TRADE_ACTION_REMOVE: "cancel",
#     mt5.TRADE_ACTION_CLOSE_BY: "exit",
# }

# r_position_maps = {
#     mt5.ORDER_TYPE_BUY: "buy",
#     mt5.ORDER_TYPE_SELL: "sell",
#     mt5.ORDER_TYPE_BUY_LIMIT: "buy_limit",
#     mt5.ORDER_TYPE_SELL_LIMIT: "sell_limit",
#     mt5.ORDER_TYPE_BUY_STOP: "buy_stop",
#     mt5.ORDER_TYPE_SELL_STOP: "sell_stop",
#     mt5.ORDER_TYPE_BUY_STOP_LIMIT: "buy_stop_limit",
#     mt5.ORDER_TYPE_SELL_STOP_LIMIT: "sell_stop_limit",
#     mt5.ORDER_TYPE_CLOSE_BY: "exit",
# }

# r_filling_map = {
#     mt5.ORDER_FILLING_FOK: "full",
#     mt5.ORDER_FILLING_IOC: "available",
#     mt5.ORDER_FILLING_RETURN: "return",
# }

# r_time_map = {
#     mt5.ORDER_TIME_GTC: "valid_till_canceled",
#     mt5.ORDER_TIME_DAY: "valid_day",
#     mt5.ORDER_TIME_SPECIFIED: "valid_time_specified",
#     mt5.ORDER_TIME_SPECIFIED_DAY: "valid_time_specified_day",
# }