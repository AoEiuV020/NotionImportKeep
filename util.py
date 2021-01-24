import glob
import os
from datetime import datetime
from random import choice
from uuid import uuid1

from notion.block import TextBlock
from notion.collection import Collection


def create_collection(client, name) -> Collection:
    cp = client.current_space.add_page(name)
    print('create block', cp.id)
    cp.type = 'collection_view_page'
    cap = client.get_block(cp.id)
    cr = client.create_record('collection', parent=cap, schema=get_default_schema())
    cap.collection = client.get_collection(cr)
    cap.title = name
    cv = cap.views.add_new('board')
    cv.group_by = 'labels'
    return cap.collection


def list_google_keep_json_file(path):
    json_list = glob.glob1(path, '*.json')
    if len(json_list) != 0:
        return path, json_list
    real_path = os.path.join(path, 'Google Keep')
    if not os.path.exists(real_path):
        real_path = os.path.join(path, 'Takeout', 'Google Keep')
    if not os.path.exists(real_path):
        return path, []
    return real_path, glob.glob1(real_path, '*.json')


def import_keep_row(client, co, row, jmap, sha256):
    with client.as_atomic_transaction():
        for key in ['title', 'isTrashed', 'isPinned', 'isArchived']:
            print('set property', key, '=', jmap[key])
            row.__setattr__(key, jmap[key])
        modify_time = datetime.fromtimestamp(jmap['userEditedTimestampUsec'] / 1000 / 1000)
        print('set userEditedTimestampUsec', '=', modify_time)
        row.userEditedTimestampUsec = modify_time
        label_list = list(o['name'] for o in jmap['labels'])
        print('set labels', '=', label_list)
        for label in label_list:
            if create_label(co, label):
                print('create label', repr(label))
        row.labels = label_list
        print('set sha256', '=', sha256)
        row.sha256 = sha256
        print('set text content', jmap['textContent'])
    # 不能在事务里创建block，有点弱了，
    row.children.add_new(TextBlock, title=jmap['textContent'])


def get_default_schema():
    return {
        "title": {"name": "title", "type": "title"},
        "isTrashed": {"name": "isTrashed", "type": "checkbox"},
        "isPinned": {"name": "isPinned", "type": "checkbox"},
        "isArchived": {"name": "isArchived", "type": "checkbox"},
        'userEditedTimestampUsec': {'name': 'userEditedTimestampUsec', 'type': 'date'},
        "sha256": {"name": "sha256", "type": "text"},
        "labels": {
            "name": "labels",
            "type": "multi_select",
            "options": [],
        }
    }


def create_label(collection, value) -> bool:
    try:
        add_new_multi_select_value(collection, 'labels', value)
        return True
    except ValueError:
        pass


# https://github.com/jamalex/notion-py/issues/51
def add_new_multi_select_value(collection, prop, value, color=None):
    """`prop` is the name of the multi select property."""
    if color is None:
        colors = [
            "default",
            "gray",
            "brown",
            "orange",
            "yellow",
            "green",
            "blue",
            "purple",
            "pink",
            "red",
        ]
        color = choice(colors)

    collection_schema = collection.get("schema")
    prop_schema = next(
        (v for k, v in collection_schema.items() if v["name"] == prop), None
    )
    if not prop_schema:
        raise ValueError(
            f'"{prop}" property does not exist on the collection!'
        )
    if prop_schema["type"] != "multi_select":
        raise ValueError(f'"{prop}" is not a multi select property!')

    # 原代码当一个选项都没有时会崩溃，这里添加空判断，
    if 'options' not in prop_schema:
        prop_schema['options'] = []

    dupe = next(
        (o for o in prop_schema["options"] if o["value"] == value), None
    )
    if dupe:
        raise ValueError(f'"{value}" already exists in the schema!')

    prop_schema["options"].append(
        {"id": str(uuid1()), "value": value, "color": color}
    )
    collection.set("schema", collection_schema)