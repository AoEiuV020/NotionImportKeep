import glob
import os
from datetime import datetime
from random import choice
from uuid import uuid1

from notion.block import TextBlock, ImageBlock, TodoBlock, AudioBlock
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
    folder = os.path.join(path, 'Google Keep')
    if not os.path.exists(folder):
        folder = os.path.join(path, 'Takeout', 'Google Keep')
    if not os.path.exists(folder):
        return path, []
    return folder, glob.glob1(folder, '*.json')


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
            # noinspection PyBroadException
            try:
                label_list = list(o['name'] for o in jmap['labels'])
            except Exception:
                label_list = []
            print('set labels', '=', label_list)
            for label in label_list:
                if create_label(co, label):
                    print('create label', repr(label))
            if label_list:
                row.labels = label_list
            print('set sha256', '=', sha256)
            row.sha256 = sha256


def import_text_content(row, jmap):
    if 'textContent' not in jmap:
        return
    text_content = jmap['textContent']
    if not text_content:
        print('empty text content')
        return
    children = row.children
    if len(children) and isinstance(children[0], TextBlock) and children[0].title_plaintext == text_content:
        print('skip text content')
    else:
        if len(children) and isinstance(children[0], TextBlock):
            print('remove old text block len', len(children[0].title_plaintext))
            children[0].remove()
        print('set text content len', len(text_content))
        rb = row.children.add_new(TextBlock, title_plaintext=text_content, language='Plain Text')
        assert rb
        # 已有图片的情况插入的文本移动到开头，用move_to是因为不支持插入指定位置，
        rb.move_to(row, 'first-child')


def import_attachments(row, folder, jmap):
    if 'attachments' not in jmap:
        return
    children = row.children
    index = 0
    if len(children) > index and isinstance(children[index], TextBlock):
        index += 1
    for i, res in enumerate(jmap['attachments']):
        real_index = index + i
        file_path = res['filePath']
        assert file_path
        mime_type = res['mimetype']
        assert '/' in mime_type
        file_type = mime_type.split('/')[0]
        assert file_type
        if file_type == 'image':
            block_type = ImageBlock
        elif file_type == 'audio':
            block_type = AudioBlock
        else:
            print('skip attachment not supported file_type', file_type, 'file_path', file_path)
            continue
        full_path = os.path.join(folder, file_path)
        if not os.path.exists(full_path):
            print(file_type, 'not found', repr(full_path))
            img_list = glob.glob1(folder, os.path.splitext(file_path)[0] + '*')
            if len(img_list):
                full_path = os.path.join(folder, img_list[0])
                print('real', file_type, 'found', full_path)
            else:
                print('skip attachment not found', file_type, 'file_path', file_path)
                continue
        file_name = os.path.split(full_path)[1]
        # 判断如果数据对不上，后续的子节点全部清空，
        while len(children) > real_index \
                and (not isinstance(children[real_index], block_type)
                     or file_name not in children[index].source):
            print('remove child', children[real_index])
            children[real_index].remove()
        if len(children) == real_index:
            print('create', file_type, full_path)
            ib = row.children.add_new(block_type)
            assert ib
            print('upload', file_type, full_path)
            ib.upload_file(full_path)
        else:
            print('skip', file_type, full_path)


def import_list_content(row, jmap):
    # noinspection PyBroadException
    try:
        list_content = jmap['listContent']
    except Exception:
        print('empty list content')
        return
    children = row.children
    index = 0
    if len(children) > index and not isinstance(children[index], TodoBlock):
        index += 1
        if len(children) > index and not isinstance(children[index], TodoBlock):
            index += 1
    for i, cb in enumerate(list_content):
        real_index = index + i
        # 判断如果数据对不上，后续的子节点全部清空，
        while len(children) > real_index \
                and (not isinstance(children[real_index], TodoBlock)
                     or children[real_index].title != cb['text']
                     or children[real_index].checked != cb['isChecked']):
            print('remove child', children[real_index])
            children[real_index].remove()
        if len(children) == real_index:
            print('create checkbox, title', repr(cb['text']), 'checked', repr(cb['isChecked']))
            assert children.add_new(TodoBlock, title=cb['text'], checked=cb['isChecked'])
        else:
            print('skip checkbox, title', repr(cb['text']), 'checked', repr(cb['isChecked']))


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
