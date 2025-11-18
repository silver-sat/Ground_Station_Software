DROP TABLE IF EXISTS transmissions;
CREATE TABLE transmissions(
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    timestamp NOT NULL DEFAULT (datetime('now', 'subsec')),
    command NOT NULL, 
    status NOT NULL DEFAULT 'pending'
);
DROP TABLE IF EXISTS responses;
CREATE TABLE responses(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp NOT NULL DEFAULT (datetime('now', 'subsec')),
    response NOT NULL
);
DROP TABLE IF EXISTS settings;
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value DEFAULT (datetime('now', 'subsec'))
);