from __future__ import annotations

import hmac
import time
from hashlib import sha256
from typing import Dict, Mapping

import httpx

from ..config import VenueConfig
from .base import OrderBookLevel, SimulatedConnector, VenueConnector

BINANCE_REST = {
    "live": "https://api.binance.com",
    "testnet": "https://testnet.binance.vision",
}


class BinanceConnector(VenueConnector):
    """Minimal synchronous Binance Spot connector supporting testnet/live."""

    def __init__(self, config: VenueConfig, *, profile: str = "paper") -> None:
        super().__init__(config)
        self.profile = profile
        endpoint = config.rest_endpoint or BINANCE_REST.get("testnet" if profile == "testnet" else "live", "")
        self._client = httpx.Client(base_url=endpoint, timeout=httpx.Timeout(10.0, read=20.0))
        self._time_offset = 0.0

    # --- public helpers -------------------------------------------------
    def _timestamp(self) -> int:
        return int(time.time() * 1000 + self._time_offset)

    def _sync_time(self) -> None:
        try:
            response = self._client.get("/api/v3/time")
            response.raise_for_status()
            payload = response.json()
            server_time = int(payload["serverTime"])
            self._time_offset = server_time - int(time.time() * 1000)
        except httpx.HTTPError:
            # Leave offset unchanged if sync fails; retries will re-sync
            pass

    def _signed_request(self, method: str, path: str, params: Dict[str, object]) -> httpx.Response:
        if not self.config.credentials.api_key or not self.config.credentials.api_secret:
            raise RuntimeError("Binance credentials are required for private endpoints")
        params = dict(params)
        params.setdefault("timestamp", self._timestamp())
        params.setdefault("recvWindow", self.config.recv_window_ms)
        query = "&".join(f"{key}={params[key]}" for key in sorted(params.keys()))
        signature = hmac.new(
            self.config.credentials.api_secret.encode("utf-8"),
            query.encode("utf-8"),
            sha256,
        ).hexdigest()
        params["signature"] = signature
        headers = {"X-MBX-APIKEY": self.config.credentials.api_key}
        request = self._client.build_request(method, path, params=params, headers=headers)
        response = self._client.send(request)
        if response.status_code == 401:
            # clock skew or expired signature; resync and retry once
            self._sync_time()
            params["timestamp"] = self._timestamp()
            query = "&".join(f"{key}={params[key]}" for key in sorted(params.keys()) if key != "signature")
            signature = hmac.new(
                self.config.credentials.api_secret.encode("utf-8"),
                query.encode("utf-8"),
                sha256,
            ).hexdigest()
            params["signature"] = signature
            request = self._client.build_request(method, path, params=params, headers=headers)
            response = self._client.send(request)
        response.raise_for_status()
        return response

    # --- interface implementation --------------------------------------
    def refresh_order_books(self) -> Mapping[str, OrderBookLevel]:
        books: Dict[str, OrderBookLevel] = {}
        for pair in self.config.trading_pairs:
            symbol = self.symbol_for_exchange(pair)
            response = self._client.get("/api/v3/ticker/bookTicker", params={"symbol": symbol})
            response.raise_for_status()
            payload = response.json()
            books[pair] = OrderBookLevel(
                bid=float(payload["bidPrice"]),
                ask=float(payload["askPrice"]),
                timestamp=time.time(),
            )
        self.update_cached_books(books)
        return books

    def place_order(self, *, symbol: str, side: str, quantity: float) -> Dict[str, float]:
        qty = self.quantize_quantity(quantity)
        books = self.cached_books() or self.refresh_order_books()
        book = books[symbol]
        price = self.quantize_price(book.ask if side.lower() == "buy" else book.bid)
        params: Dict[str, object] = {
            "symbol": self.symbol_for_exchange(symbol),
            "side": side.upper(),
            "type": "LIMIT",
            "timeInForce": "IOC",
            "quantity": f"{qty:.{self.config.quantity_precision}f}",
            "price": f"{price:.{self.config.price_precision}f}",
            "newOrderRespType": "RESULT",
        }
        path = "/api/v3/order/test" if self.config.simulate else "/api/v3/order"
        response = self._signed_request("POST", path, params)
        data = response.json() if response.content else params
        return {
            "orderId": data.get("orderId", "test-order"),
            "symbol": symbol,
            "side": side,
            "price": price,
            "executedQty": float(data.get("executedQty", qty)),
            "status": data.get("status", "FILLED" if self.config.simulate else "NEW"),
            "timestamp": time.time(),
        }

    def cancel_order(self, *, symbol: str, order_id: str) -> Dict[str, float]:
        params = {"symbol": self.symbol_for_exchange(symbol), "orderId": order_id}
        response = self._signed_request("DELETE", "/api/v3/order", params)
        payload = response.json()
        return {"symbol": symbol, "orderId": order_id, "status": payload.get("status", "CANCELED")}

    def order_status(self, *, symbol: str, order_id: str) -> Dict[str, float]:
        params = {"symbol": self.symbol_for_exchange(symbol), "orderId": order_id}
        response = self._signed_request("GET", "/api/v3/order", params)
        payload = response.json()
        payload["symbol"] = symbol
        return payload

    def balances(self) -> Mapping[str, float]:
        if self.config.simulate:
            return self.cached_balances()
        response = self._signed_request("GET", "/api/v3/account", {})
        payload = response.json()
        balances: Dict[str, float] = {}
        for balance in payload.get("balances", []):
            free = float(balance.get("free", 0))
            locked = float(balance.get("locked", 0))
            balances[balance["asset"]] = free + locked
        self._balances = balances
        return balances

    def cached_balances(self) -> Mapping[str, float]:
        return dict(self._balances)


class BinanceSimulatedConnector(SimulatedConnector):
    """Fallback simulated connector when simulate=true."""

    pass
