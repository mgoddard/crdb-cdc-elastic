# CockroachDB: CDC to Elasticsearch

Full text indexing and search is such a common feature of applications these days.
Users expect to be able to find a restaurant, a product, a movie review, or any
of a number of other things quickly by entering a few search terms into a user
interface.  Many of these apps are built using a relational database as the data
store, so the apps aren't generally dedicated to search, but incorporate that as
an added feature.

For developers using CockroachDB, the full text search options really don't yet
exist within the database itself.  Though CockroachDB does support Levenshtein and
Soundex, and these can be combined in novel ways to support fuzzy matching of shorter
data elements, the effort to build out full text search is just beginning.

Having said that, CockroachDB does support _changefeeds_, or _Change Data Capture_ (CDC).
Changefeeds allow you to configure an event stream based on changes to tables in the DB,
and these can be emitted into a message queue (e.g. Kafka), an S3 bucket, or even just
an HTTP(S) endpoint.  Once configured, any INSERT, UPDATE, DELETE generates an event
which can be acted on by another process.  This process could even be something like
Elasticsearch, which would provide that full text index and search capability.  Back
in August 2020, I mentioned this in a [blog post](https://www.cockroachlabs.com/blog/full-text-indexing-search/)
on full text search in CockroachDB and I just realized I hadn't yet found a demo of
this integration.  That's the motivation for this post.

## Solution Overview

I opted to run this in a VM deployed in Google Cloud Platform, in the us-central1 region, because
CockroachDB Serverless is available in that region.  Of the various types of endpoints currently
available for [CREATE CHANGEFEED](https://www.cockroachlabs.com/docs/stable/create-changefeed.html),
there isn't one which lines up directly with what Elasticsearch expects as input, so I needed to
create a [Python Flask app](./cdc_http.py) which acts as the adapter between CockroachDB and Elasticsearch.
I also decided to just run the Elasticsearch instance right there on that VM.  Since having all this
communication be encrypted seemed like a good idea, I ran an Nginx instance as a proxy for both
the Flask app and Elasticsearch. Let's Encrypt handles the SSL certificates.


## Setup in CockroachDB

* Create the simple table to store documents found on the Web:
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
* [Phrase query](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-match-query-phrase.html)
* [Filtering search results](https://www.elastic.co/guide/en/elasticsearch/reference/7.0/search-request-source-filtering.html)
* [Trigrams in CockroachDB](https://github.com/cockroachdb/cockroach/issues/41285)

