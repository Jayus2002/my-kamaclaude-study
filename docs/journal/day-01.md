## 一些收获
项目名 my-kamaclaude 由uv建立
包名 my-kamaclaude
命令入口 my_kamaclaude:main 包下面的main函数

学习了 argparse 库的一些用法
```python
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", help="The message to print")
    parser.add_argument("--version", action="version", version=f"%(prog)s {version('my-kamaclaude')}")
    args = parser.parse_args()
    if args.message:
        print(args.message)
    else:
        print(datetime.now())
```