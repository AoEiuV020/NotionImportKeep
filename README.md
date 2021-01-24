# NotionImportKeep

使用notion非官方python api上传google keep笔记到notion,

先上takeout导出google keep，格式要json,  
程序运行需要输入notion网站上的键为token_v2的cookies，  
然后输入包含json文件夹路径，  
最后需要导入的notion数据库block的id，留空表示由脚本自动在根节点创建数据库，

导入过程很容易因为网络问题停止，所以支持指定block id，用于断点续传，  
指定同一个block导入时会自动跳过已经上传了的记事，

```shell
pip install setuptools
pip install notion
python3 main.py
```

[https://github.com/jamalex/notion-py](https://github.com/jamalex/notion-py)