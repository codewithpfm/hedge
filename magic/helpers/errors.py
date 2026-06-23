MT5_ERROR_10004 = 10004
MT5_ERROR_10006 = 10006
MT5_ERROR_10007 = 10007
MT5_ERROR_10008 = 10008
MT5_ERROR_10009 = 10009
MT5_ERROR_10010 = 10010
MT5_ERROR_10011 = 10011
MT5_ERROR_10012 = 10012
MT5_ERROR_10013 = 10013
MT5_ERROR_10014 = 10014
MT5_ERROR_10015 = 10015
MT5_ERROR_10016 = 10016
MT5_ERROR_10017 = 10017
MT5_ERROR_10018 = 10018
MT5_ERROR_10019 = 10019
MT5_ERROR_10020 = 10020
MT5_ERROR_10021 = 10021
MT5_ERROR_10022 = 10022
MT5_ERROR_10023 = 10023
MT5_ERROR_10024 = 10024
MT5_ERROR_10025 = 10025
MT5_ERROR_10026 = 10026
MT5_ERROR_10027 = 10027
MT5_ERROR_10028 = 10028
MT5_ERROR_10029 = 10029
MT5_ERROR_10030 = 10030
MT5_ERROR_10031 = 10031
MT5_ERROR_10032 = 10032
MT5_ERROR_10033 = 10033
MT5_ERROR_10034 = 10034
MT5_ERROR_10035 = 10035
MT5_ERROR_10036 = 10036
MT5_ERROR_10038 = 10038
MT5_ERROR_10039 = 10039
MT5_ERROR_10040 = 10040
MT5_ERROR_10041 = 10041
MT5_ERROR_10042 = 10042
MT5_ERROR_10043 = 10043
MT5_ERROR_10044 = 10044
MT5_ERROR_10045 = 10045
MT5_ERROR_10046 = 10046

ERROR_CODES = [
    MT5_ERROR_10004,
    MT5_ERROR_10006,
    MT5_ERROR_10007,
    # MT5_ERROR_10008,
    # MT5_ERROR_10009,
    MT5_ERROR_10010,
    MT5_ERROR_10011,
    MT5_ERROR_10012,
    MT5_ERROR_10013,
    MT5_ERROR_10014,
    MT5_ERROR_10015,
    MT5_ERROR_10016,
    MT5_ERROR_10017,
    MT5_ERROR_10018,
    MT5_ERROR_10019,
    MT5_ERROR_10020,
    MT5_ERROR_10021,
    MT5_ERROR_10022,
    MT5_ERROR_10023,
    MT5_ERROR_10024,
    MT5_ERROR_10025,
    MT5_ERROR_10026,
    MT5_ERROR_10027,
    MT5_ERROR_10028,
    MT5_ERROR_10029,
    MT5_ERROR_10030,
    MT5_ERROR_10031,
    MT5_ERROR_10032,
    MT5_ERROR_10033,
    MT5_ERROR_10034,
    MT5_ERROR_10035,
    MT5_ERROR_10036,
    MT5_ERROR_10038,
    MT5_ERROR_10039,
    MT5_ERROR_10040,
    MT5_ERROR_10041,
    MT5_ERROR_10042,
    MT5_ERROR_10043,
    MT5_ERROR_10044,
    MT5_ERROR_10045,
    MT5_ERROR_10046,
]

ERROR_REASONS = {
    MT5_ERROR_10004: "Requote",
    MT5_ERROR_10006: "Request rejected",
    MT5_ERROR_10007: "Request canceled by trader",
    MT5_ERROR_10008: "Order placed",
    MT5_ERROR_10009: "Request completed",
    MT5_ERROR_10010: "Only part of the request was completed",
    MT5_ERROR_10011: "Request processing error",
    MT5_ERROR_10012: "Request canceled by timeout",
    MT5_ERROR_10013: "Invalid request",
    MT5_ERROR_10014: "Invalid volume in the request",
    MT5_ERROR_10015: "Invalid price in the request",
    MT5_ERROR_10016: "Invalid stops in the request",
    MT5_ERROR_10017: "Trade is disabled",
    MT5_ERROR_10018: "Market is closed",
    MT5_ERROR_10019: "There is not enough money to complete the request",
    MT5_ERROR_10020: "Prices changed",
    MT5_ERROR_10021: "There are no quotes to process the request",
    MT5_ERROR_10022: "Invalid order expiration date in the request",
    MT5_ERROR_10023: "Order state changed",
    MT5_ERROR_10024: "Too frequent requests",
    MT5_ERROR_10025: "No changes in request",
    MT5_ERROR_10026: "Autotrading disabled by server",
    MT5_ERROR_10027: "Autotrading disabled by client terminal",
    MT5_ERROR_10028: "Request locked for processing",
    MT5_ERROR_10029: "Order or position frozen",
    MT5_ERROR_10030: "Invalid order filling type",
    MT5_ERROR_10031: "No connection with the trade server",
    MT5_ERROR_10032: "Operation is allowed only for live accounts",
    MT5_ERROR_10033: "The number of pending orders has reached the limit",
    MT5_ERROR_10034: "The volume of orders and positions for the symbol has reached the limit",
    MT5_ERROR_10035: "Incorrect or prohibited order type",
    MT5_ERROR_10036: "Position with the specified POSITION_IDENTIFIER has already been closed",
    MT5_ERROR_10038: "A close volume exceeds the current position volume",
    MT5_ERROR_10039: "A close order already exists for a specified position",
    MT5_ERROR_10040: "The number of open positions simultaneously present on an account can be limited by the server settings",
    MT5_ERROR_10041: "The pending order activation request is rejected, the order is canceled",
    MT5_ERROR_10042: "The request is rejected, because the 'Only long positions are allowed' rule is set for the symbol",
    MT5_ERROR_10043: "The request is rejected, because the 'Only short positions are allowed' rule is set for the symbol",
    MT5_ERROR_10044: "The request is rejected, because the 'Only position closing is allowed' rule is set for the symbol",
    MT5_ERROR_10045: "The request is rejected, because 'Position closing is allowed only by FIFO rule' flag is set for the trading account",
    MT5_ERROR_10046: "The request is rejected, because the 'Opposite positions on a single symbol are disabled' rule is set for the trading account",
}


def check_error(code: int) -> bool:
    """
    Check the error code and return the reason
    """
    if code in ERROR_CODES:
        return True
    else:
        return False
        
def get_message(code: int) -> str:
    """
    Get the error message
    """
    return ERROR_REASONS[code]