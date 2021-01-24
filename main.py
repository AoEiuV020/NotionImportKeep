import hashlib
import json
import os
from datetime import datetime

from notion.block import TextBlock
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
print('create database', name)
client = NotionClient(token_v2=token)
if block is None:
    co = util.create_collection(client, name)
else:
    co = client.get_block(block).collection

json_name = list_file[-1]
json_content = open(os.path.join(real_path, json_name), 'rb').read()
sha256 = hashlib.sha256(json_content).hexdigest()
print('import note from', repr(json_name), 'hash', repr(sha256))
jmap = json.loads(str(json_content, encoding='utf-8'))
print('add row')
row = co.add_row()
for key in ['title', 'isTrashed', 'isPinned', 'isArchived']:
    print('set property', key, '=', jmap[key])
    row.__setattr__(key, jmap[key])
modifyTime = datetime.fromtimestamp(jmap['userEditedTimestampUsec'] / 1000 / 1000)
print('set userEditedTimestampUsec', '=', modifyTime)
row.userEditedTimestampUsec = modifyTime
with client.as_atomic_transaction():
    label_list = list(o['name'] for o in jmap['labels'])
    print('set labels', key, '=', label_list)
    for label in label_list:
        if util.create_label(co, label):
            print('create label', repr(label))
    row.labels = label_list
print('set sha256', '=', sha256)
row.sha256 = sha256
print('set text content', jmap['textContent'])
row.children.add_new(TextBlock, title=jmap['textContent'])
print('ok', repr(json_name), 'hash', repr(sha256))
