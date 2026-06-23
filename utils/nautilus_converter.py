from nautilus_trader.model.objects import Price, Quantity, Currency
from nautilus_trader.model.instruments import CurrencyPair
from nautilus_trader.model.identifiers import InstrumentId, Symbol, Venue


def setup_forex_instrument(symbol: str, venue: str = "MT5"):
    """
    Setup default specifications for Forex pairs.
    """
    # Robustly handle symbol vs full instrument_id
    if f".{venue}" in symbol:
        symbol_only = symbol.replace(f".{venue}", "")
    else:
        symbol_only = symbol

    instr_id = InstrumentId(Symbol(symbol_only), Venue(venue))

    # Generic Forex detection
    if "JPY" in symbol:
        p_prec = 3
        p_inc = 1e-3
    else:
        p_prec = 5
        p_inc = 1e-5

    base_currency = Currency.from_str(symbol_only[:3])
    quote_currency = Currency.from_str(symbol_only[3:])

    instrument = CurrencyPair(
        instr_id,
        Symbol(symbol_only),
        base_currency,
        quote_currency,
        p_prec,
        0,  # size_precision
        Price(p_inc, p_prec),
        Quantity(1000, 0),    # FIX: size_increment (1000 units = 0.01 lot)
        Quantity(1, 0),       # multiplier
        Quantity(100_000, 0), # lot_size
    )
    return instrument
