# Architectural Decisions

## ADR-001: Connectors
Paper mode continues to use simulated connectors for deterministic tests, while production profiles instantiate signed REST clients for Binance Spot and OKX Spot. Both implementations share the `VenueConnector` interface so runtime selection is driven entirely by config.

## ADR-002: SAFE_MODE Defaults
SAFE_MODE is enabled for all environments and boots in HOLD for paper/testnet. Resuming requires double confirmation to satisfy the two-key requirement.

## ADR-003: SQLite Journal
A lightweight SQLite journal captures trading events for replay, recon, and tax export without external dependencies. Production deployments can swap in Postgres by adjusting `StorageConfig`.
