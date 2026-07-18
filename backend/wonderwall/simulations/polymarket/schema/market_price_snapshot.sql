CREATE TABLE IF NOT EXISTS market_price_snapshot (
    market_id   INTEGER NOT NULL,
    round       INTEGER NOT NULL CHECK (round >= 0),
    price_yes   REAL NOT NULL CHECK (price_yes >= 0.0 AND price_yes <= 1.0),
    reserve_a   REAL NOT NULL CHECK (reserve_a > 0.0),
    reserve_b   REAL NOT NULL CHECK (reserve_b > 0.0),
    PRIMARY KEY (market_id, round),
    FOREIGN KEY (market_id) REFERENCES market(market_id)
);
