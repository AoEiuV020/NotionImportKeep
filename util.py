import glob
import os
from datetime import datetime
from random import choice
from uuid import uuid1

from notion.block import TextBlock, ImageBlock
from notion.collection import Collection


def create_collection(client, name) -> Collection:
    cp = client.current_space.add_page(name)
    print('created block id', cp.id)
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
    if row.sha256 == sha256:
        print('skip row properties')
    else:
        # 不能在事务里创建记录和block，有点弱了，
        with client.as_atomic_transaction():
            for key in ['title', 'isTrashed', 'isPinned', 'isArchived']:
                print('set property', key, '=', jmap[key])
                row.__setattr__(key, jmap[key])
            modify_time = datetime.fromtimestamp(jmap['userEditedTimestampUsec'] / 1000 / 1000)
            print('set userEditedTimestampUsec', '=', modify_time)
            row.userEditedTimestampUsec = modify_time
            try:
                label_list = list(o['name'] for o in jmap['labels'])
            except Exception:
                label_list = []
            print('set labels', '=', label_list)
            for label in label_list:
                if create_label(co, label):
                    print('create label', repr(label))
            row.labels = label_list
            print('set sha256', '=', sha256)
            row.sha256 = sha256
    text_content = jmap['textContent']
    children = row.children
    if len(children) and isinstance(children[0], TextBlock) and children[0].title == text_content:
        print('skip text content')
    else:
        if len(children) and isinstance(children[0], TextBlock):
            print('remove old text block', children[0].title)
            children[0].remove()
        print('set text content len', len(text_content))
        rb = row.children.add_new(TextBlock, title=text_content)
        assert rb
        # 已有图片的情况插入的文本移动到开头，用move_to是因为不支持插入指定位置，
        rb.move_to(row, 'first-child')


def import_keep_cover(row, real_path, jmap):
    img = None
    # noinspection PyBroadException
    try:
        img = jmap['attachments'][0]['filePath']
    except Exception:
        pass
    if img is not None:
        print('add image', repr(img))
        img_full_path = os.path.join(real_path, img)
        if not os.path.exists(img_full_path):
            print('image not found', repr(img_full_path))
            img_list = glob.glob1(real_path, os.path.splitext(img)[0] + '*')
            if len(img_list):
                img_full_path = os.path.join(real_path, img_list[0])
                print('real image found', img_full_path)
        if os.path.exists(img_full_path):
            children = row.children
            if len(children) > 1 and \
                    isinstance(children[1], ImageBlock) and \
                    os.path.split(img_full_path)[1] in children[1].source:
                print('skip image')
            else:
                if len(children) > 1 and isinstance(children[1], ImageBlock):
                    print('remove old image block', children[1].source)
                    children[1].remove()
                print('create image', img_full_path)
                # 只能是ImageBlock，上传的图片地址设置为封面会失效，
                ib = row.children.add_new(ImageBlock)
                assert ib
                ib.upload_file(img_full_path)
                if len(children) > 1:
                    ib.move_to(children[0], 'after')


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
