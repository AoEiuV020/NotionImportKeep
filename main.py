#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import json
import os

from notion.client import NotionClient
from requests.packages.urllib3.util.retry import Retry

import util

token = None
path = None
block = None
name = 'Google Keep'
if os.path.exists('local.py'):
    exec(open('local.py').read())
if token is None:
    token = input('please input notion cookie token_v2,')
if path is None:
    path = input('please input google keep takeout path contains json files,')
if block is None:
    block = input('please input notion database block id, press enter for auto create,')

print('token is', repr(token))
print('path is', repr(path))
folder, list_file = util.list_google_keep_json_file(path)
print('json file count', repr(len(list_file)))
retry = Retry(
    5,
    backoff_factor=0.3,
    status_forcelist=(500, 501, 502, 503, 504),
    method_whitelist=("POST", "HEAD", "TRACE", "GET", "PUT", "OPTIONS", "DELETE"),
)
client = NotionClient(token_v2=token, client_specified_retry=retry)
if not block:
    print('create block name', name)
    co = util.create_collection(client, name)
else:
    print('get database', block)
    co = client.get_block(block).collection

for json_name in list_file:
    json_content = open(os.path.join(folder, json_name), 'rb').read()
    sha256 = hashlib.sha256(json_content).hexdigest()
    print('import note from', repr(json_name), 'sha256', repr(sha256))
    jmap = json.loads(str(json_content, encoding='utf-8'))
    exists_rows = co.get_rows(search=sha256)
    if len(exists_rows):
        print('exists row')
        row = exists_rows[0]
    else:
        print('create row')
        row = co.add_row()
    util.import_keep_row(client, co, row, jmap, sha256)
    util.import_text_content(row, jmap)
    util.import_attachments(row, folder, jmap)
    util.import_list_content(row, jmap)
    print('ok', repr(json_name), 'sha256', repr(sha256))
