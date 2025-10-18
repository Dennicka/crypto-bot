from __future__ import annotations

import base64
import hmac
import json
import time
from hashlib import sha256
from typing import Dict, Mapping

import httpx

from ..config import VenueConfig
from .base import OrderBookLevel, SimulatedConnector, VenueConnector

OKX_REST = "https://www.okx.com"


class OKXConnector(VenueConnector):
    """Synchronous OKX spot connector with testnet support."""

    def __init__(self, config: VenueConfig, *, profile: str = "paper") -> None:
        super().__init__(config)
        endpoint = config.rest_endpoint or OKX_REST
        headers = {"Content-Type": "application/json"}
        if profile == "testnet":
            headers["X-OKX-SIMULATED-TRADING"] = "1"
        self.profile = profile
        self._client = httpx.Client(base_url=endpoint, headers=headers, timeout=httpx.Timeout(10.0, read=20.0))

    def symbol_for_exchange(self, symbol: str) -> str:  # type: ignore[override]
        overrides = self.config.symbol_overrides
        if symbol in overrides:
            return overrides[symbol]
        return symbol.replace("/", "-").upper()

    def _timestamp(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())

    def _signed_request(
        self, method: str, path: str, *, params: Dict[str, object] | None = None, body: Dict[str, object] | None = None
    ) -> httpx.Response:
        params = params or {}
        body = body or {}
        query = ""
        if params:
            query = "?" + "&".join(f"{key}={params[key]}" for key in sorted(params))
        payload = json.dumps(body) if body else ""
        timestamp = self._timestamp()
        message = f"{timestamp}{method.upper()}{path}{query}{payload}".encode("utf-8")
        if not self.config.credentials.api_key or not self.config.credentials.api_secret or not self.config.credentials.passphrase:
            raise RuntimeError("OKX credentials are required for private endpoints")
        secret = self.config.credentials.api_secret.encode("utf-8")
        signature = base64.b64encode(hmac.new(secret, message, sha256).digest()).decode("utf-8")
        headers = {
            "OK-ACCESS-KEY": self.config.credentials.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.config.credentials.passphrase,
        }
        if self.profile == "testnet":
            headers["X-OKX-SIMULATED-TRADING"] = "1"
        request = self._client.build_request(method, path, params=params, json=body, headers=headers)
        response = self._client.send(request)
        if response.status_code == 401:
            # retry with a new timestamp once
            timestamp = self._timestamp()
            message = f"{timestamp}{method.upper()}{path}{query}{payload}".encode("utf-8")
            signature = base64.b64encode(hmac.new(secret, message, sha256).digest()).decode("utf-8")
            headers["OK-ACCESS-SIGN"] = signature
            headers["OK-ACCESS-TIMESTAMP"] = timestamp
            request = self._client.build_request(method, path, params=params, json=body, headers=headers)
            response = self._client.send(request)
        response.raise_for_status()
        payload_json = response.json()
        if payload_json.get("code") not in ("0", 0, None):
            raise RuntimeError(str(payload_json))
        return response

    def refresh_order_books(self) -> Mapping[str, OrderBookLevel]:
        books: Dict[str, OrderBookLevel] = {}
        for pair in self.config.trading_pairs:
            inst_id = self.symbol_for_exchange(pair)
            response = self._client.get("/api/v5/market/ticker", params={"instId": inst_id})
            response.raise_for_status()
            data = response.json()
            if not data.get("data"):
                continue
            ticker = data["data"][0]
            books[pair] = OrderBookLevel(
                bid=float(ticker["bidPx"]),
                ask=float(ticker["askPx"]),
                timestamp=time.time(),
            )
        self.update_cached_books(books)
        return books

    def place_order(self, *, symbol: str, side: str, quantity: float) -> Dict[str, float]:
        qty = self.quantize_quantity(quantity)
        books = self.cached_books() or self.refresh_order_books()
        book = books[symbol]
        price = self.quantize_price(book.ask if side.lower() == "buy" else book.bid)
        body = {
            "instId": self.symbol_for_exchange(symbol),
            "tdMode": "cash",
            "side": "buy" if side.lower() == "buy" else "sell",
            "ordType": "limit",
            "px": f"{price:.{self.config.price_precision}f}",
            "sz": f"{qty:.{self.config.quantity_precision}f}",
        }
        path = "/api/v5/trade/order"
        if self.config.simulate:
            # simulated mode uses the trade/order algo but we skip private call
            return {
                "orderId": f"okx-sim-{int(time.time() * 1000)}",
                "symbol": symbol,
                "side": side,
                "price": price,
                "executedQty": qty,
                "status": "FILLED",
                "timestamp": time.time(),
            }
        response = self._signed_request("POST", path, body=body)
        payload = response.json()
        order_id = payload.get("data", [{}])[0].get("ordId", "")
        return {
            "orderId": order_id,
            "symbol": symbol,
            "side": side,
            "price": price,
            "executedQty": qty,
            "status": "NEW",
            "timestamp": time.time(),
        }

    def cancel_order(self, *, symbol: str, order_id: str) -> Dict[str, float]:
        body = {"instId": self.symbol_for_exchange(symbol), "ordId": order_id}
        response = self._signed_request("POST", "/api/v5/trade/cancel-order", body=body)
        payload = response.json()
        status = payload.get("data", [{}])[0].get("state", "canceled")
        return {"symbol": symbol, "orderId": order_id, "status": status}

    def order_status(self, *, symbol: str, order_id: str) -> Dict[str, float]:
        body = {"instId": self.symbol_for_exchange(symbol), "ordId": order_id}
        response = self._signed_request("POST", "/api/v5/trade/order", body=body)
        payload = response.json()
        details = payload.get("data", [{}])[0]
        details["symbol"] = symbol
        return details

    def balances(self) -> Mapping[str, float]:
        if self.config.simulate:
            return self.cached_balances()
        response = self._signed_request("GET", "/api/v5/account/balance")
        payload = response.json()
        balances: Dict[str, float] = {}
        for detail in payload.get("data", []):
            for balance in detail.get("details", []):
                total = float(balance.get("cashBal", 0.0))
                balances[balance["ccy"]] = total
        self._balances = balances
        return balances

    def cached_balances(self) -> Mapping[str, float]:
        return dict(self._balances)


class OKXSimulatedConnector(SimulatedConnector):
    pass
