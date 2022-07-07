# CockroachDB: CDC to Elasticsearch

What is this?
Why?

## Setup in CockroachDB

* Create the simple table to store documents found on the Web
```
CREATE TABLE docs
(
  uri STRING PRIMARY KEY
  , content STRING NOT NULL
  , ts TIMESTAMP DEFAULT NOW()
);
```

* Enable rangefeeds:
```
SET CLUSTER SETTING kv.rangefeed.enabled = true;
```

* Create the HTTP changefeed into the Python Flask endpoint:
```
CREATE CHANGEFEED FOR TABLE docs
INTO 'https://cdc.la-cucaracha.net/cdc/'
WITH full_table_name, updated;
```

## References

* [Elastic cheat sheet](https://gist.github.com/ruanbekker/e8a09604b14f37e8d2f743a87b930f93)

