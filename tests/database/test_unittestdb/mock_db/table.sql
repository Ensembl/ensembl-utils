CREATE TABLE gibberish (
    id    INTEGER NOT NULL,
    grp   VARCHAR(20) DEFAULT '',
    value INT DEFAULT NULL,
    PRIMARY KEY (id, grp)
);
CREATE INDEX id_idx ON gibberish (id);
