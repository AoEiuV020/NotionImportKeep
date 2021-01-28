#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import hashlib
import json
import os
import threading
import traceback

from notion.client import NotionClient
from requests.packages.urllib3.util.retry import Retry

import util
from blocking_executor import BlockingExecutor
from util import logger

token = None
path = None
block = None
thread_count = 30
name = 'Google Keep'
if os.path.exists('local.py'):
    exec(open('local.py').read())
if token is None:
    token = input('please input notion cookie token_v2,')
if path is None:
    path = input('please input google keep takeout path contains json files,')
if block is None:
    block = input('please input notion database block id, press enter for auto create,')

logger('token is', repr(token))
logger('path is', repr(path))
folder, list_file = util.list_google_keep_json_file(path)
logger('json file count', repr(len(list_file)))
retry = Retry(
    5,
    backoff_factor=0.3,
    status_forcelist=(500, 501, 502, 503, 504),
    method_whitelist=("POST", "HEAD", "TRACE", "GET", "PUT", "OPTIONS", "DELETE"),
)
client = NotionClient(token_v2=token, client_specified_retry=retry)
if not block:
    logger('create block name', name)
    (mco, block) = util.create_collection(client, name)
else:
    logger('get database', block)
    mco = client.get_block(block).collection


def import_keep_row(json_name):
    co = None
    try:
        # noinspection PyUnresolvedReferences
        co = threading.current_thread().co
    except:
        pass
    if not co:
        client = NotionClient(token_v2=token, client_specified_retry=retry)
        co = client.get_block(block).collection
        threading.current_thread().co = co
    json_content = open(os.path.join(folder, json_name), 'rb').read()
    sha256 = hashlib.sha256(json_content).hexdigest()
    logger('import note from', repr(json_name), 'sha256', repr(sha256))
    jmap = json.loads(str(json_content, encoding='utf-8'))
    exists_rows = co.get_rows(search=sha256)
    if len(exists_rows):
        logger('exists row')
        row = exists_rows[0]
    else:
        logger('create row')
        row = co.add_row()
    util.import_keep_row(co, row, jmap, sha256)
    util.import_text_content(row, jmap)
    util.import_attachments(row, folder, jmap)
    util.import_list_content(row, jmap)
    logger('ok', repr(json_name), 'sha256', repr(sha256))


executor = BlockingExecutor(thread_count, 1)
try:
    for json_name in list_file:
        executor.submit(import_keep_row, json_name)
except:
    traceback.print_exc()
    logger('import error')
    os._exit(1)
logger('wait thread')
executor.shutdown()
