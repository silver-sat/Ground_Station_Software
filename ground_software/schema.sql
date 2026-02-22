DROP TABLE IF EXISTS transmissions;
CREATE TABLE transmissions(
    id INTEGER PRIMARY KEY AUTOINCREMENT, 
    timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    message_sequence INTEGER NOT NULL UNIQUE,
    command NOT NULL, 
    status NOT NULL DEFAULT 'pending'
);

DROP TABLE IF EXISTS responses;
CREATE TABLE responses(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    message_sequence INTEGER NOT NULL UNIQUE,
    response NOT NULL
);

DROP TABLE IF EXISTS radio_logs;
CREATE TABLE radio_logs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    message_sequence INTEGER NOT NULL UNIQUE,
    log_line TEXT NOT NULL
);

DROP TABLE IF EXISTS settings;
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value DEFAULT CURRENT_TIMESTAMP
);

DROP VIEW IF EXISTS filtered_transmissions;
CREATE VIEW filtered_transmissions AS
SELECT
    id,
    timestamp,
    message_sequence,
    substr(command, 3, length(command) - 3) AS command
FROM transmissions
WHERE substr(command, 2, 1) <> x'0D';

DROP VIEW IF EXISTS filtered_responses;
CREATE VIEW filtered_responses AS
SELECT
    id,
    timestamp,
    message_sequence,
    substr(response, 3, length(response) - 3) AS response
FROM responses
WHERE CAST(SUBSTR(response, 3, 5) AS TEXT) NOT IN ('ACK D', 'RES D');

DROP VIEW IF EXISTS combined_messages;
CREATE VIEW combined_messages AS
SELECT
    message_sequence,
    timestamp,
    'transmission' AS type,
    CAST(SUBSTR(command, 3, LENGTH(command) - 3) AS TEXT) AS message
FROM transmissions
WHERE SUBSTR(command, 2, 1) <> x'0D'
UNION ALL
SELECT
    message_sequence,
    timestamp,
    'response' AS type,
    CAST(SUBSTR(response, 3, LENGTH(response) - 3) AS TEXT) AS message
FROM responses
WHERE CAST(SUBSTR(response, 3, 5) AS TEXT) NOT IN ('ACK D', 'RES D')
UNION ALL
SELECT
    message_sequence,
    timestamp,
    'radio_log' AS type,
    log_line AS message
FROM radio_logs
ORDER BY message_sequence

;

DROP VIEW IF EXISTS radio_log_rssi;
CREATE VIEW radio_log_rssi AS
SELECT
    id,
    timestamp,
    message_sequence,
    log_line,
    CAST(
        TRIM(
            REPLACE(
                REPLACE(
                    CASE
                        WHEN instr(lower(substr(log_line, instr(lower(log_line), 'n: rssi'))), 'dbm') > 0 THEN
                            substr(
                                log_line,
                                instr(lower(log_line), 'n: rssi') + 7,
                                instr(lower(substr(log_line, instr(lower(log_line), 'n: rssi') + 7)), 'dbm') - 1
                            )
                        ELSE
                            substr(log_line, instr(lower(log_line), 'n: rssi') + 7)
                    END,
                    '=',
                    ''
                ),
                ':',
                ''
            )
        ) AS REAL
    ) AS rssi_dbm
FROM radio_logs
WHERE instr(lower(log_line), 'n: rssi') > 0;
