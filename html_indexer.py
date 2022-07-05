#!/usr/bin/env python3

import psycopg2
import psycopg2.errorcodes
from psycopg2.errors import SerializationFailure
from bs4 import BeautifulSoup
import sys, os
import html
import time
import requests
import random

#
# Prior to running, set this environment variable:
#
#   $ export DB_CONN_STR="postgres://root@localhost:26257/defaultdb"
#

"""
DROP TABLE IF EXISTS docs;
CREATE TABLE docs (uri STRING PRIMARY KEY, content STRING NOT NULL, ts TIMESTAMP DEFAULT NOW());

SET CLUSTER SETTING kv.rangefeed.enabled = true;

CREATE CHANGEFEED FOR TABLE docs
INTO 'http://localhost:3000/'
WITH updated, full_table_name;

"""

db_conn_str = os.getenv("DB_CONN_STR")
if db_conn_str is None:
  print("DB_CONN_STR must be set to the URL of the DB")
  sys.exit(1)

if len(sys.argv) < 2:
  print("Usage: %s uri [uri2 ...]" % sys.argv[0])
  sys.exit(1)

def insert_row(conn, uri, content):
  with conn.cursor() as cur:
    cur.execute("INSERT INTO docs (uri, content) VALUES (%s, %s);", (uri, content))
    conn.commit()

# https://github.com/cockroachlabs/hello-world-python-psycopg2/blob/master/example.py
def run_transaction(conn, op, max_retries=3):
  with conn:
    for retry in range(1, max_retries + 1):
      try:
        op(conn)
        return
      except SerializationFailure as e:
        print("got error: %s", e)
        conn.rollback()
        print("EXECUTE SERIALIZATION_FAILURE BRANCH")
        sleep_ms = (2**retry) * 0.1 * (random.random() + 0.5)
        print("Sleeping %s seconds", sleep_ms)
        time.sleep(sleep_ms)
      except psycopg2.Error as e:
        print("got error: %s", e)
        print("EXECUTE NON-SERIALIZATION_FAILURE BRANCH")
        raise e
    raise ValueError(f"transaction did not succeed after {max_retries} retries")

def index_uri (conn, uri):
  html = ""
  resp = requests.get(uri)
  html = resp.text
  soup = BeautifulSoup(html, 'html.parser')
  text = soup.get_text()
  run_transaction(conn, lambda conn: insert_row(conn, uri, text))

# main()
t0 = time.time()
conn = psycopg2.connect(db_conn_str)
for uri in sys.argv[1:]:
  print("Indexing uri " + uri + " now ...")
  index_uri(conn, uri)
t1 = time.time()
print("Total time: " + str(t1 - t0) + " s")
conn.close()

