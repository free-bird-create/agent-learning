system = {
    "role": "system",
    "content": "你是编程助手。依据提供的信息回答，不要编造用户要求。",
}

history = [
    {
        "role": "user",
        "content": "我要做笔记整理程序。不能联网，不能把文件内容上传到外部服务。",
    },
    {"role": "assistant", "content": "明白，按本地离线处理设计。"},
    {"role": "user", "content": "第一版只需要命令行界面。"},
    {"role": "assistant", "content": "好的，暂时不做图形界面。"},
    {"role": "user", "content": "我的笔记都是 Markdown 文件。"},
    {"role": "assistant", "content": "好的，输入文件格式是 Markdown。"},
]

question = {
    "role": "user",
    "content": "请给出笔记整理程序的三步实现方案，并说明应遵守哪些限制。",
}

cases = {
    "完整历史": [system] + history + [question],
    "最近两条历史": [system] + history[-2:] + [question],
}

for name, messages in cases.items():
    print(f"\n===== {name}：{len(messages)} 条消息 =====")
    for message in messages:
        print(f'{message["role"]}: {message["content"]}')