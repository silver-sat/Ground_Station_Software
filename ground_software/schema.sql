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

DROP VIEW IF EXISTS filtered_transmissions;
CREATE VIEW filtered_transmissions AS
SELECT
    id,
    timestamp,
    substr(command, 3, length(command) - 3) AS command
FROM transmissions
WHERE substr(command, 2, 1) <> x'0D';

DROP VIEW IF EXISTS filtered_responses;
CREATE VIEW filtered_responses AS
SELECT
    id,
    timestamp,
    substr(response, 3, length(response) - 3) AS response
FROM responses
WHERE CAST(SUBSTR(response, 3, 5) AS TEXT) NOT IN ('ACK D', 'RES D');

DROP VIEW IF EXISTS combined_messages;
CREATE VIEW combined_messages AS
SELECT
    timestamp,
    'transmission' AS type,
    CAST(SUBSTR(command, 3, LENGTH(command) - 3) AS TEXT) AS message
FROM transmissions
WHERE SUBSTR(command, 2, 1) <> x'0D'
UNION ALL
SELECT
    timestamp,
    'response' AS type,
    CAST(SUBSTR(response, 3, LENGTH(response) - 3) AS TEXT) AS message
FROM responses
WHERE CAST(SUBSTR(response, 3, 5) AS TEXT) NOT IN ('ACK D', 'RES D')
ORDER BY timestamp
