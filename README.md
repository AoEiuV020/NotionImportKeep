# NotionImportKeep

使用notion非官方python api上传google keep笔记到notion,

先上takeout导出google keep，格式要json,  
程序运行需要输入notion网站上的键为token_v2的cookies，  
然后输入包含json文件夹路径，  
最后需要导入的notion数据库block的id，留空表示由脚本自动在根节点创建数据库，

```shell
pip install setuptools
pip install notion
python3 main.py
```

[https://github.com/jamalex/notion-py](https://github.com/jamalex/notion-py)