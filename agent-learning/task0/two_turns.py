from getpass import getpass
from openai import OpenAI

client = OpenAI(
    api_key=getpass("DeepSeek API Key: ").strip(),
    base_url="https://api.deepseek.com",
    timeout=60.0,
    max_retries=0,
)

messages = [
    {"role": "system", "content": "你是一位Python老师，回答简洁具体。"}
]

questions = [
    "给我两个适合Python初学者的小项目，编号为1和2，每个用一句话描述。",
    "第二个项目最小可运行的版本，需要哪些功能？先不要写代码。",
]

for turn, question in enumerate(questions, start=1):#注意这个语法
    messages.append({"role": "user", "content": question})

    print(f"\n第 {turn} 轮，发送 {len(messages)} 条消息")
    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=messages,
        max_tokens=512,
        extra_body={"thinking": {"type": "disabled"}},
    )

    answer = response.choices[0].message.content
    print("用户：", question)
    print("助手：", answer)

    messages.append({"role": "assistant", "content": answer})
    
print("=====message=====")
print(messages)