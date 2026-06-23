"""MT5 live execution client (+ config, factory).

Translates Nautilus ``SubmitOrder`` / close-position commands into MT5 trade
requests and dispatches the resulting fills back to the Nautilus execution
engine. Designed for the dual-position ``HedgeStrategy`` running under
``OmsType.HEDGING`` — each opening fill becomes its own MT5 position
(identified by the MT5 ticket), and ``close_position()`` from the strategy
is routed to MT5 with the position ticket so only that leg is closed.

The config + factory sit alongside the client so ``TradingNode`` can wire
them via ``add_exec_client_factory``.
"""
from __future__ import annotations

import asyncio

import MetaTrader5 as mt5  # type: ignore
from nautilus_trader.cache.cache import Cache
from nautilus_trader.common.component import LiveClock, MessageBus
from nautilus_trader.config import LiveExecClientConfig
from nautilus_trader.core.uuid import UUID4
from nautilus_trader.execution.messages import CancelOrder, SubmitOrder
from nautilus_trader.live.execution_client import LiveExecutionClient
from nautilus_trader.live.factories import LiveExecClientFactory
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import (
    AccountType,
    LiquiditySide,
    OmsType,
    OrderSide,
    OrderType,
)
from nautilus_trader.model.identifiers import (
    AccountId,
    ClientId,
    PositionId,
    TradeId,
    Venue,
    VenueOrderId,
)
from nautilus_trader.model.objects import (
    AccountBalance,
    Currency,
    MarginBalance,
    Money,
    Price,
    Quantity,
)
from nautilus_trader.model.orders import MarketOrder

from magic.helpers.constants import MAGIC, MT5_ACCOUNT
from nautilus_mt5.data_client import MT5_VENUE_STR, MT5InstrumentProvider


class MT5ExecutionClient(LiveExecutionClient):
    """Routes Nautilus orders to MT5 and reports fills back to the engine.

    Only ``MarketOrder`` is supported (matches ``HedgeStrategy._submit`` which
    always uses the order factory's ``market(...)`` helper).
    """

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        client_id: ClientId,
        venue: Venue,
        account_id: AccountId,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
        instrument_provider: MT5InstrumentProvider,
        broker_magic: int = MAGIC,
    ) -> None:
        super().__init__(
            loop=loop,
            client_id=client_id,
            venue=venue,
            oms_type=OmsType.HEDGING,
            account_type=AccountType.MARGIN,
            base_currency=None,  # multi-currency margin account
            instrument_provider=instrument_provider,
            msgbus=msgbus,
            cache=cache,
            clock=clock,
        )
        self._set_account_id(account_id)
        self.magic = broker_magic

    # ── Lifecycle ────────────────────────────────────────────────────────
    async def _connect(self) -> None:
        if not mt5.initialize():
            self._log.error("MT5 initialize failed in ExecClient")
            return
        await self._instrument_provider.initialize()
        for inst in self._instrument_provider.list_all():
            self._cache.add_instrument(inst)
        await self._publish_account_state()
        self._log.info("MT5ExecutionClient connected.")

    async def _disconnect(self) -> None:
        mt5.shutdown()
        self._log.info("MT5ExecutionClient disconnected.")

    async def _publish_account_state(self) -> None:
        info = mt5.account_info()
        if info is None:
            self._log.error("MT5 account_info() returned None")
            return
        ccy = Currency.from_str(info.currency) if info.currency else USD
        balance = AccountBalance(
            total=Money(float(info.balance), ccy),
            locked=Money(float(info.margin), ccy),
            free=Money(float(info.balance) - float(info.margin), ccy),
        )
        margin = MarginBalance(
            initial=Money(float(info.margin), ccy),
            maintenance=Money(float(info.margin), ccy),
        )
        self.generate_account_state(
            balances=[balance],
            margins=[margin],
            reported=True,
            ts_event=self._clock.timestamp_ns(),
        )

    # ── Order routing ────────────────────────────────────────────────────
    async def _submit_order(self, command: SubmitOrder) -> None:
        order = command.order
        if not isinstance(order, MarketOrder):
            self._log.error(
                f"MT5ExecutionClient only supports MarketOrder; got {type(order).__name__}"
            )
            self.generate_order_rejected(
                strategy_id=order.strategy_id,
                instrument_id=order.instrument_id,
                client_order_id=order.client_order_id,
                reason="unsupported_order_type",
                ts_event=self._clock.timestamp_ns(),
            )
            return

        # OrderSubmitted — we're about to send to MT5
        self.generate_order_submitted(
            strategy_id=order.strategy_id,
            instrument_id=order.instrument_id,
            client_order_id=order.client_order_id,
            ts_event=self._clock.timestamp_ns(),
        )

        symbol = order.instrument_id.symbol.value
        mt5_side = (
            mt5.ORDER_TYPE_BUY if order.side == OrderSide.BUY else mt5.ORDER_TYPE_SELL
        )
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            self._reject(order, f"no_tick_for_{symbol}")
            return
        px = tick.ask if mt5_side == mt5.ORDER_TYPE_BUY else tick.bid

        # MT5 volume is in *lots* (not contract units); the strategy sizes in
        # contract units, so convert via the instrument's lot_size.
        instrument = self._cache.instrument(order.instrument_id)
        if instrument is None:
            self._reject(order, f"no_instrument_{order.instrument_id}")
            return
        lots = float(order.quantity.as_double()) / float(instrument.lot_size.as_double())

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lots,
            "type": mt5_side,
            "price": px,
            "magic": self.magic,
            "deviation": 20,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
            "comment": f"Nautilus:{order.client_order_id.value}",
        }

        # Close-leg path: ``HedgeStrategy.close_position(pos)`` produces a
        # SubmitOrder with ``position_id`` set. In MT5 HEDGING mode, closing a
        # specific leg requires the ``position`` ticket on the trade request.
        # We stored the MT5 ticket as the Nautilus position_id at fill time,
        # so the value here parses straight back to the ticket.
        if command.position_id is not None:
            try:
                request["position"] = int(command.position_id.value)
            except ValueError:
                self._log.warning(
                    f"position_id {command.position_id} is not a numeric MT5 ticket"
                )

        result = await asyncio.get_event_loop().run_in_executor(
            None, mt5.order_send, request
        )

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            reason = result.comment if result else str(mt5.last_error())
            self._reject(order, reason)
            return

        venue_order_id = VenueOrderId(str(result.order))
        # For an opening fill, the MT5 ticket *is* the position identifier we
        # want Nautilus to use going forward. For a close, we reuse the ticket
        # passed in via command.position_id so the same Nautilus position is
        # closed.
        venue_position_id = (
            command.position_id
            if command.position_id is not None
            else PositionId(str(result.order))
        )

        self.generate_order_accepted(
            strategy_id=order.strategy_id,
            instrument_id=order.instrument_id,
            client_order_id=order.client_order_id,
            venue_order_id=venue_order_id,
            ts_event=self._clock.timestamp_ns(),
        )
        self.generate_order_filled(
            strategy_id=order.strategy_id,
            instrument_id=order.instrument_id,
            client_order_id=order.client_order_id,
            venue_order_id=venue_order_id,
            venue_position_id=venue_position_id,
            trade_id=TradeId(str(result.deal) if result.deal else UUID4().value),
            order_side=order.side,
            order_type=OrderType.MARKET,
            last_qty=Quantity(
                float(result.volume) * float(instrument.lot_size.as_double()),
                instrument.size_precision,
            ),
            last_px=Price(float(result.price), instrument.price_precision),
            quote_currency=instrument.quote_currency,
            commission=Money(0.0, instrument.quote_currency),
            liquidity_side=LiquiditySide.TAKER,
            ts_event=self._clock.timestamp_ns(),
        )
        self._log.info(
            f"MT5 fill: ticket={result.order} deal={result.deal} "
            f"{order.side.name} {result.volume} lots @ {result.price}"
        )

    async def _cancel_order(self, command: CancelOrder) -> None:
        # Market orders fill immediately on MT5 — there is nothing to cancel
        # in the current strategy. Logged for visibility if the strategy ever
        # routes a working order.
        self._log.warning(
            f"cancel_order requested for {command.client_order_id} but the MT5 "
            f"market-order pipeline has nothing to cancel"
        )

    # ── helpers ──────────────────────────────────────────────────────────
    def _reject(self, order, reason: str) -> None:
        self._log.error(f"MT5 order rejected ({reason}): {order.client_order_id}")
        self.generate_order_rejected(
            strategy_id=order.strategy_id,
            instrument_id=order.instrument_id,
            client_order_id=order.client_order_id,
            reason=reason,
            ts_event=self._clock.timestamp_ns(),
        )


# ─────────────────────────────────────────────────────────────────────────
# Config + factory (TradingNode wires the client via these)
# ─────────────────────────────────────────────────────────────────────────
class MT5ExecClientConfig(LiveExecClientConfig, frozen=True):
    broker_magic: int = MAGIC
    account_login: int = MT5_ACCOUNT


class MT5LiveExecClientFactory(LiveExecClientFactory):
    @staticmethod
    def create(  # type: ignore[override]
        loop: asyncio.AbstractEventLoop,
        name: str,
        config: MT5ExecClientConfig,
        msgbus: MessageBus,
        cache: Cache,
        clock: LiveClock,
    ) -> MT5ExecutionClient:
        venue = Venue(MT5_VENUE_STR)
        provider = MT5InstrumentProvider(venue=MT5_VENUE_STR)
        return MT5ExecutionClient(
            loop=loop,
            client_id=ClientId(name),
            venue=venue,
            account_id=AccountId(f"{MT5_VENUE_STR}-{config.account_login}"),
            msgbus=msgbus,
            cache=cache,
            clock=clock,
            instrument_provider=provider,
            broker_magic=config.broker_magic,
        )
