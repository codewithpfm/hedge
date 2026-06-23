"""Per-ticker instrument specifications for ATR risk-based position sizing.

`HedgeStrategy._position_qty` sizes every leg with the standard MT5 risk
formula::

    risk_amount = balance * risk_percent          # quote currency
    sl_pips     = atr / pip_size                   # ATR expressed as a pip count
    lots        = risk_amount / (sl_pips * pip_value)
    units       = lots * contract_size

so each traded symbol needs the four numbers below. Spot forex and spot metals
all obey the same formula once these are filled in — switching from a forex
pair to ``XAUUSD`` is just a new row here, no code change.

Fields
------
pip_size      : price increment of one pip (0.0001 forex, 0.01 JPY pairs,
                0.1 for gold).
pip_value     : profit/loss, in the instrument's **quote currency**, of a
                one-pip move on ONE standard lot. For a spot instrument this
                equals ``pip_size * contract_size``; it is stored explicitly
                because for some instruments the broker quotes it directly.
contract_size : base-asset units in one standard lot.
min_lot       : smallest lot size the broker will accept.

``pip_value`` is denominated in the quote currency on purpose:
``HedgeStrategy`` reads the account balance in the instrument's quote currency,
so ``risk_amount`` and ``pip_value`` share a currency and the formula needs no
FX conversion.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class InstrumentSpec:
    pip_size: float
    pip_value: float       # quote-currency value of 1 pip on 1 standard lot
    contract_size: float   # base-asset units per standard lot
    min_lot: float


# symbol  ->                      pip_size, pip_value, contract_size, min_lot
_SPECS: dict[str, InstrumentSpec] = {
    "EURUSD": InstrumentSpec(0.0001,   10.0,      100_000.0,   0.01),
    "GBPUSD": InstrumentSpec(0.0001,   10.0,      100_000.0,   0.01),
    "AUDUSD": InstrumentSpec(0.0001,   10.0,      100_000.0,   0.01),
    "NZDUSD": InstrumentSpec(0.0001,   10.0,      100_000.0,   0.01),
    "USDCHF": InstrumentSpec(0.0001,   10.0,      100_000.0,   0.01),  # quote CHF
    "USDCAD": InstrumentSpec(0.0001,   10.0,      100_000.0,   0.01),  # quote CAD
    "USDJPY": InstrumentSpec(0.01,     1_000.0,   100_000.0,   0.01),  # quote JPY
    "EURJPY": InstrumentSpec(0.01,     1_000.0,   100_000.0,   0.01),  # quote JPY
    "XAUUSD": InstrumentSpec(0.1,      10.0,      100.0,       0.01),  # gold: 100 oz/lot
}


def get_instrument_spec(ticker: str) -> InstrumentSpec:
    """Return the :class:`InstrumentSpec` for ``ticker``.

    Accepts a bare symbol (``"USDJPY"``) or a Nautilus instrument id
    (``"USDJPY.SIM"`` / ``"XAUUSD.MT5"``). Raises :class:`KeyError` with an
    actionable message for an unknown symbol — sizing must never silently fall
    back to a wrong contract spec.
    """
    symbol = ticker.split(".")[0].upper()
    try:
        return _SPECS[symbol]
    except KeyError:
        raise KeyError(
            f"No instrument spec for '{symbol}'. Add a row to "
            f"utils/instrument_specs.py before trading it."
        ) from None
