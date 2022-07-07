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
so it's simplified to just a single table oriented towards storing data taken from URLs.

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



## References

* [Elastic cheat sheet](https://gist.github.com/ruanbekker/e8a09604b14f37e8d2f743a87b930f93)
* [Phrase query](https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-match-query-phrase.html)
* [Filtering search results](https://www.elastic.co/guide/en/elasticsearch/reference/7.0/search-request-source-filtering.html)
* [Trigrams in CockroachDB](https://github.com/cockroachdb/cockroach/issues/41285)

