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

The example shown here is mainly to illustrate the CockroachDB / Elasticsearch integration,
so it's simplified to just a single table which is oriented to storing data taken from URLs.

## Solution Overview

I opted to run this in a VM deployed in Google Cloud Platform, in the us-central1 region, because
CockroachDB Serverless is available in that region.  Of the various types of endpoints currently
available for [CREATE CHANGEFEED](https://www.cockroachlabs.com/docs/stable/create-changefeed.html),
there isn't one which lines up directly with what Elasticsearch expects as input, so I needed to
create a [Python Flask app](./cdc_http.py) which acts as the adapter between CockroachDB and Elasticsearch.
I also decided to just run the Elasticsearch instance right there on that VM.  Since having all this
communication be encrypted seemed like a good idea, I ran an Nginx instance as a proxy for both
the Flask app and Elasticsearch. [Let's Encrypt](https://letsencrypt.org/getting-started/)
handles the SSL certificates. I used [Google Domains](https://domains.google.com/) for DNS
so that my Let's Encrypt setup would work. Finally, I kind of used this VM as a "base camp" and
ran the [HTML indexer](./html_indexer.py) from there as well.

## Setup: Infrastructure

* Ubuntu 22.04 LTS running on `e2-standard-2` VM with 64 GB SSD
* Network, subnet were `default`, where port 443 was open for HTTPS traffic
* On the VM: `sudo apt update`, then `sudo apt install postgresql-client`
* Elasticsearch (ES) installed per [this reference](https://www.elastic.co/guide/en/elasticsearch/reference/current/targz.html)
* ES was started up using the default config and the "Password for the elastic user" was recorded for later
* Contents of this GitHub repo were transferred to the VM (e.g. `git clone https://github.com/mgoddard/crdb-cdc-elastic.git`)
* Installed pip: `sudo apt install python3-pip`
* Python dependencies got installed: `sudo pip3 install -r requirements.txt`
* Installed Nginx: `sudo apt install -y nginx`
* Set up an 'A' record in DNS for the VM, using its external IP address (in my case, it resolved to "cdc.la-cucaracha.net")
* Followed [this procedure](https://certbot.eff.org/) to get Let's Encrypt SSL certs for my Nginx installation
* Replaced the resulting `/etc/nginx/nginx.conf` with an edited version of [this file](./nginx.conf), then restarted Nginx
* Set up a CockroachDB Serverless instance via [this UI](https://cockroachlabs.cloud/login) in the same region as the VM
* Created a CockroachDB user and grabbed the credentials using that same UI.  I stored this in a file, `CC_cred.txt`.
* Downloaded the CA cert per the "Download CA Cert (Required only once)" instructions on the Serverless UI
* Started up the Flask CDC endpoint:
```
$ export ES_PASSWD="that password recorded earlier"
$ nohup ./cdc_http.py > cdc.log 2>&1 </dev/null &
```

## Setup: CockroachDB

* Log into the CockroachDB Serverless instance (I use the `psql` CLI out of habit):
```
$ psql $( cat ./CC_cred.txt )
psql (14.4 (Ubuntu 14.4-0ubuntu0.22.04.1), server 13.0.0)
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_128_GCM_SHA256, bits: 128, compression: off)
Type "help" for help.

```

* Create the simple table to store documents found on the Web:
```
defaultdb=> CREATE TABLE docs
(
  uri STRING PRIMARY KEY
  , content STRING NOT NULL
  , ts TIMESTAMP DEFAULT NOW()
);
CREATE TABLE
```

* Enable rangefeeds (this may have been set up already in Serverless):
```
defaultdb=> SET CLUSTER SETTING kv.rangefeed.enabled = true;
SET CLUSTER SETTING
```

* Create the HTTP changefeed into the Python Flask endpoint:
```
defaultdb=> CREATE CHANGEFEED FOR TABLE docs
INTO 'https://cdc.la-cucaracha.net/cdc/'
WITH full_table_name, updated;
       job_id
--------------------
 777046877208477698
(1 row)
```

## Using it

I'm running the following from the VM.

* Install an additional dependency for the HTML indexer: `sudo pip3 install beautifulsoup4`

* Set an environment variable for the DB connection: `export DB_CONN_STR=$( cat ../CC_cred.txt )`

* Index some URLS:
```
$ ./html_indexer.py https://www.cockroachlabs.com/blog/admission-control-in-cockroachdb/ https://www.cockroachlabs.com/blog/how-to-choose-db-index-keys/ https://www.cockroachlabs.com/docs/v21.1/example-apps.html https://www.cockroachlabs.com/docs/v22.1/multiregion-overview.html https://www.cockroachlabs.com/blog/can-i-scale/ https://www.cockroachlabs.com/blog/sigmod-2022-cockroachdb-multi-region-paper/ https://www.cockroachlabs.com/blog/living-without-atomic-clocks/ https://github.com/cockroachdb/pebble https://www.cockroachlabs.com/blog/netflix-media-infrastructure/ https://www.cockroachlabs.com/blog/full-text-indexing-search/
Indexing uri https://www.cockroachlabs.com/blog/admission-control-in-cockroachdb/ now ...
Indexing uri https://www.cockroachlabs.com/blog/how-to-choose-db-index-keys/ now ...
Indexing uri https://www.cockroachlabs.com/docs/v21.1/example-apps.html now ...
Indexing uri https://www.cockroachlabs.com/docs/v22.1/multiregion-overview.html now ...
Indexing uri https://www.cockroachlabs.com/blog/can-i-scale/ now ...
Indexing uri https://www.cockroachlabs.com/blog/sigmod-2022-cockroachdb-multi-region-paper/ now ...
Indexing uri https://www.cockroachlabs.com/blog/living-without-atomic-clocks/ now ...
Indexing uri https://github.com/cockroachdb/pebble now ...
Indexing uri https://www.cockroachlabs.com/blog/netflix-media-infrastructure/ now ...
Indexing uri https://www.cockroachlabs.com/blog/full-text-indexing-search/ now ...
Total time: 5.30757999420166 s
```

* Back in the SQL CLI, check that they were inserted:
```
defaultdb=> select uri, length(content), ts from docs order by 2 desc;
                                      uri                                       | length |             ts
--------------------------------------------------------------------------------+--------+----------------------------
 https://www.cockroachlabs.com/blog/admission-control-in-cockroachdb/           |  24985 | 2022-07-07 15:33:32.685422
 https://www.cockroachlabs.com/docs/v22.1/multiregion-overview.html             |  21300 | 2022-07-07 15:33:33.672853
 https://www.cockroachlabs.com/blog/living-without-atomic-clocks/               |  20184 | 2022-07-07 15:33:35.000319
 https://www.cockroachlabs.com/blog/how-to-choose-db-index-keys/                |  16958 | 2022-07-07 15:33:32.970703
 https://www.cockroachlabs.com/blog/can-i-scale/                                |  14654 | 2022-07-07 15:33:34.196958
 https://www.cockroachlabs.com/blog/full-text-indexing-search/                  |  13387 | 2022-07-07 15:33:36.789336
 https://www.cockroachlabs.com/blog/netflix-media-infrastructure/               |  12859 | 2022-07-07 15:33:36.247931
 https://github.com/cockroachdb/pebble                                          |  12504 | 2022-07-07 15:33:35.708953
 https://www.cockroachlabs.com/blog/sigmod-2022-cockroachdb-multi-region-paper/ |   9454 | 2022-07-07 15:33:34.70964
 https://www.cockroachlabs.com/docs/v21.1/example-apps.html                     |   9373 | 2022-07-07 15:33:33.307314
(10 rows)
```

* Try an ES search:

The [search script](./es_search.py) runs a "phrase query" based on the terms provided to it via
command line arguments.  The returned value, if there were any search hits, includes metadata
about the search along with the values of the fields in the table as well as up to four highlighted
matching snippets of up to 80 characters in length.  Feel free to adjust the script to suit your
needs.

```
$ export ES_PASSWD="ad7yMq3nrg+2bGz-QWe*"
$ ./es_search.py database region
{
  "_shards": {
    "failed": 0,
    "skipped": 0,
    "successful": 1,
    "total": 1
  },
  "hits": {
    "hits": [
      {
        "_id": "public-docs-https://www.cockroachlabs.com/docs/v22.1/multiregionoverview.html",
        "_ignored": [
          "content.keyword"
        ],
        "_index": "defaultdb",
        "_score": 1.8865218,
        "highlight": {
          "content": [
            "<em>Database</em> <em>region</em> is a geographic region in which a database operates.",
            "You must choose a <em>database</em> <em>region</em> from the list of available cluster regions.",
            "To add another <em>database</em> <em>region</em>, use the ALTER DATABASE ...",
            "Each <em>database</em> <em>region</em> can only belong to one super region."
          ]
        }
      }
    ],
    "max_score": 1.8865218,
    "total": {
      "relation": "eq",
      "value": 1
    }
  },
  "timed_out": false,
  "took": 16
}
```
## Final Thoughts

That completes the little tour of CDC from CockroachDB to Elasticsearch.  Looking back at that original
blog post mentioned above, I was a little cavalier in saying you could just use CDC to Elasticsearch for
search, so now I feel a bit better about it.  It's been quite a while since I've done much work with
Lucene, Solr, or Elasticsearch, and it's changing all the time, so most likely my example here is pretty
basic.  In any case, I hope it inspires you to explore this type of integration should the need arise.

Thank you for taking the time to read this over!

## References

* [Elastic cheat sheet](https://gist.github.com/ruanbekker/e8a09604b14f37e8d2f743a87b930f93)
* [Phrase query](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-match-query-phrase.html)
* [Filtering search results](https://www.elastic.co/guide/en/elasticsearch/reference/7.0/search-request-source-filtering.html)
* [Trigrams in CockroachDB](https://github.com/cockroachdb/cockroach/issues/41285)
* Examples of [log output](./cdc_http_log_examples.txt) and output of [SHOW JOBS](./show_jobs_es_down.txt)

