import hashlib
import json
import os

from notion.client import NotionClient

import util

token = None
path = None
block = None
name = 'Google Keep'
if os.path.exists('local.py'):
    exec(open('local.py').read())
if token is None:
    token = input('please input notion cookie token_v2')
if path is None:
    path = input('please input google keep takeout path contains json files')

print('token is', repr(token))
print('path is', repr(path))
real_path, list_file = util.list_google_keep_json_file(path)
print('json file count', repr(len(list_file)))
client = NotionClient(token_v2=token)
if block is None:
    print('create database', name)
    co = util.create_collection(client, name)
else:
    print('get database', block)
    co = client.get_block(block).collection

json_name = list_file[-1]
json_content = open(os.path.join(real_path, json_name), 'rb').read()
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
util.import_keep_cover(row, real_path, jmap)
print('ok', repr(json_name), 'sha256', repr(sha256))
