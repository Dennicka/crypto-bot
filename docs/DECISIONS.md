# Architectural Decisions

## ADR-001: Simulated Connectors
To deliver deterministic tests without live exchange calls, connectors are simulated with seeded random order books. Real integrations can extend `VenueConnector` with REST/WebSocket clients while reusing the engine plumbing.

## ADR-002: SAFE_MODE Defaults
SAFE_MODE is enabled for all environments and boots in HOLD for paper/testnet. Resuming requires double confirmation to satisfy the two-key requirement.

## ADR-003: SQLite Journal
A lightweight SQLite journal captures trading events for replay, recon, and tax export without external dependencies. Production deployments can swap in Postgres by adjusting `StorageConfig`.
