# Task1 实验结果摘录

本文只保留实际运行中的关键输出，省略本机路径、HTTP 调试日志和请求追踪信息。实验数据均为虚构测试数据。

## 1. Memory 冲突更新与跨会话读取

```text
=== 初始记忆 ===
用户主要使用 Windows。

=== 新对话 ===
user: 更正一下：我现在主要使用 Linux，已经不再把 Windows 作为主要系统。

=== 模型产生的工具调用 ===
工具: update_memory
参数: 将原 operating_system Note 更新为“用户主要使用 Linux，已不再把 Windows 作为主要系统。”
结果: Memory updated successfully

=== 实验判断 ===
PASS: 模型调用 update_memory，并在原 Note 上完成了更新。

=== 全新会话读取长期记忆 ===
跨会话回答: 根据我保存的用户记忆，你目前主要使用 Linux，并且已不再将 Windows 作为主要操作系统。
```

## 2. 无 RAG 与有 RAG

问题：NOVA-17 的每周例会在什么时间、什么地点，需要携带什么？

```text
=== 不使用 RAG ===
模型表示当前消息没有提供 NOVA-17 的安排，因此无法确定。

=== BM25 检索结果 ===
#1 nova_schedule
The NOVA-17 weekly review starts at 14:30 every Tuesday in room B305.
Every participant must bring a blue access card.

=== 使用 RAG ===
NOVA-17 的每周例会为每周二 14:30，地点 B305，需要携带蓝色门禁卡。
来源: nova_schedule
```

本次数据流：

```text
问题 → BM25 检索 → 取回相关文档 → 拼入 Context → DeepSeek 生成答案
```

## 3. RAG 新旧文档冲突

两份通知的 BM25 结果：

```text
#1 nova_schedule_2026_08_20  date=2026-08-20  score=2.484700
   每周一 10:00，B201，绿色门禁卡

#2 nova_schedule_2026_09_18  date=2026-09-18  score=2.484700
   每周四 16:00，D402，黄色门禁卡
```

普通 RAG 没有获得冲突处理规则时：

```text
两份资料在时间、地点、携带物品上相互冲突，因此不能自行假定哪条有效，需要进一步确认。
```

加入新鲜度规则后：

```text
根据发布日期最新的公告 nova_schedule_2026_09_18（2026-09-18），
当前例会为每周四 16:00，地点 D402，需要携带黄色门禁卡。
```

这个结果说明 BM25 的相关性得分不负责判断版本有效性；日期进入 Context 后，仍需要明确的新鲜度或版本规则。
