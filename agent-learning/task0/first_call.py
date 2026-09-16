#system user tool assistant
from getpass import getpass
from openai import OpenAI

api_key = getpass("Deepseek APIKEY: ").strip()#不会显示

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
    timeout=60.0,
    max_retries=0
)
"""message = [{"role":"system","content":"你是一位面向Python开发者的老师。解释概念时使用具体的编程术语，不使用生活类比。"}#role用来标记消息身份
            ,{"role":"user","content":"用两句话解释什么是API"}]

print("正在发送请求……")
response = client.chat.completions.create(
    model="deepseek-flash",
    messages=message,
    max_tokens=256,
    extra_body={"thinking":{"type":"disabled"}}
)
print("\n模型回答: ")
print(response.choices[0].message.content)
print("\nToken用量 :")
print(response.usage)"""
system = {
    "role": "system",
    "content": "只根据对话中提供的信息回答；不知道就说不知道，不要猜。"
}

history = [
    {"role": "user", "content": "我的实验编号是 R728，请记住。"}
]

question = {"role": "user", "content": "我的实验编号是什么？"}

cases = [
    ("有历史", [system] + history + [question]),#加法在干什么
    ("无历史", [system, question]),
]

for name, messages in cases:
    print(f"\n--- {name} ---")
    print("本次发送的消息：", messages)

    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
        max_tokens=128,
        extra_body={"thinking": {"type": "disabled"}},
    )

    print("模型回答：", response.choices[0].message.content)
    print(response.usage)
    print("==============")