import json
from getpass import getpass
from openai import OpenAI

client = OpenAI(
    api_key=getpass("DeepSeek API KEY: ").strip(),
    base_url="https://api.deepseek.com",
    timeout=60.0,
    max_retries=0,
)

def add(a, b):
    return a + b
def multify(a,b):
    return a*b
tools = [{
    "type": "function",
    "function": {
        "name": "add",
        "description": "计算两个数的想加的结果",
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "integer"},
                "b": {"type": "integer"},
            },
            "required": ["a", "b"],
        },
    },
}]

messages = [
    {"role": "system", "content": "计算加法时必须使用提供的工具。"},
    {"role": "user", "content": "请计算 1+1和1+2"},
]

def ask_model(tool_choice):
    return client.chat.completions.create(
        model="deepseek-flash", messages=messages, tools=tools,
        tool_choice=tool_choice, max_tokens=512,
        extra_body={"thinking": {"type": "disabled"}},
    ).choices[0].message

message = ask_model("auto")
if not message.tool_calls:
    raise RuntimeError(f"本次没有调用工具：{message.content}")
messages.append(message.model_dump(exclude_none=True))

for call in message.tool_calls:
    args = json.loads(call.function.arguments)
    print("模型请求：", call.function.name, args)
    if call.function.name != "add" or set(args) != {"a", "b"}:#键在不讲顺序的时候是不是a,b
        raise ValueError("工具名称或参数不符合预期")
    if any(type(value) is not int for value in args.values()):
        raise ValueError("加法参数必须是整数")
    result = add(args["a"], args["b"])
    print("Python 执行结果：", result)
    messages.append({
        "role": "tool", "tool_call_id": call.id, "content": str(result),
    })
answer = ask_model("none").content
messages.append({"role":"assistant","content":answer})
print("===answer===")
print(answer)
print("====message====")
print(messages)