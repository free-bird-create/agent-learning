# Task1：Context、Memory 与 RAG

实验日期：2026年9月17日至21日。笔记整理日期：2026年9月22日。

课程来源：[ai-agent-book](https://github.com/bojieli/ai-agent-book)。实验在课程代码基础上完成，我实际运行、观察并修改了 Context 压缩、长期记忆与本地 RAG 示例。本文中的设备、NOVA-17 项目和 Windows/Linux 用户信息均为实验构造的虚拟数据。

## 1. Context、Memory、RAG 的关系

我目前的理解是：**Context 是模型本次调用真正能看到的输入；Memory 和 RAG 都不能被模型自动读取，必须先由程序选出相关内容，再放进 Context。**

```text
对话历史、工具结果 ─┐
长期 Memory ────────┼─> Context ─> LLM ─> 回答或工具调用
RAG 检索资料 ───────┘
```

- **Context**：包括系统指令、当前问题、对话历史、工具结果和检索资料，受上下文窗口限制。
- **Memory**：保存与用户或长期任务有关的信息，使新会话还能取回旧信息。它是外部持久化存储，不是模型训练。
- **RAG**：根据当前问题从外部文档中检索证据，再把证据加入 Context，让模型回答原本不知道的私有或更新知识。

Memory 更关注“关于这个用户或长期状态应记住什么”，RAG 更关注“为当前问题应从知识库找什么”。两者最终都要经过检索、选择和 Context 注入才能影响模型。

## 2. Context 实验

我先用 [context_selection.py](context_selection.py) 对比完整历史和最近两条历史，观察删除早期信息后，模型可用的约束也会随之消失。随后在课程的上下文压缩实验中比较了 `no_compression`、`individual`、`combined`、`context_aware`、`citations` 和 `windowed`。

实验任务要求 Agent 从本地设备资料中比较价格、独立显存和驱动支持。不同策略最终都能生成答案，但摘要内容、证据保留程度和上下文长度不同。`context_aware` 会围绕当前问题保留信息，`citations` 额外保存来源，`windowed` 只在达到窗口阈值后压缩。

我还观察到：压缩策略的名称不代表它自动覆盖所有内容，必须检查代码实际在哪个工具结果上调用压缩器；摘要请求本身也会消耗 Token。因此不能只看最终答案或压缩比例判断策略好坏，还要检查保留了什么、遗漏了什么以及摘要成本。实际 JSON 结果保存在 [results/context_compression](results/context_compression/) 中。

## 3. Memory 实验

[memory_conflict_experiment.py](memory_conflict_experiment.py) 先写入一条虚构记忆“用户主要使用 Windows”，再提供更正信息“现在主要使用 Linux”。记忆分析 Agent 读取了旧记忆和新对话，调用 `update_memory` 更新原 Note，而不是留下两条互相冲突的记录。

```text
旧记忆：用户主要使用 Windows
新对话：现在主要使用 Linux
工具调用：update_memory
实验判断：PASS，同一个 Note 被更新
新会话回答：目前主要使用 Linux
```

这让我体会到跨会话 Memory 的基本机制：

```text
对话产生新信息
→ 记忆分析 Agent 对照已有记忆
→ add / update / delete
→ 写入外部 JSON
→ 新会话按 user_id 读取
→ 注入当前 Context
```

记忆内容由模型判断，所以仍可能漏记、误记或产生冲突，需要更新规则、日志和验证。关键运行输出见 [实验结果摘录](results/experiment_outputs.md)，持久化结果见 [memory_conflict_demo_memory.json](results/memory/memory_conflict_demo_memory.json)。

## 4. RAG 实验

### 4.1 无 RAG 与有 RAG

[rag_first_experiment.py](rag_first_experiment.py) 使用相同问题做对照：直接询问模型时，模型不知道虚构项目 NOVA-17 的例会安排；BM25 检索本地资料并将结果放入 Context 后，模型回答出“周二 14:30、B305、蓝色门禁卡”，并引用 `nova_schedule`。

```text
问题 → BM25 检索 → 取回文档 → 拼入 Context → LLM 生成答案
```

日志中的 `score=0.0000` 并非真正为零。小语料中多个查询词出现在超过一半的文档里，原始 IDF 为负，教学实现用 `max(raw_idf, 1e-6)` 设置下限。实际得分约为 `0.000006` 和 `0.000005`，只是保留四位小数时都显示为零。BM25 score 是用于相对排序的数值，不是正确率。

### 4.2 新旧资料冲突

[rag_conflict_experiment.py](rag_conflict_experiment.py) 同时提供两份高度相关但内容冲突的 NOVA-17 通知。BM25 对两份文档都给出 `2.484700`，因为它们命中的关键词相同；相关性分数本身不能判断哪份资料当前有效。

普通 Prompt 要求遇到冲突不要猜测，模型因此列出冲突。加入“同一事实冲突时采用发布日期最新的公告”后，模型选择了 2026-09-18 的新通知。

这说明日期只是数据，新鲜度规则才规定如何使用日期。更完整的知识库还应保存 `effective_from`、`valid_until`、`status`、`supersedes` 等 metadata；不能在所有场景中简单假设“发布日期最新的一定正确”。关键运行输出见 [实验结果摘录](results/experiment_outputs.md)。

## 5. 当前总结

经过这组实验，我把三者联系成了一条数据流：Context 决定模型本次能看到什么；Memory 让长期用户信息能够跨会话保存和取回；RAG 让 Agent 按问题从外部知识库寻找证据。模型最终只能利用进入 Context 的信息，因此 Agent 工程不仅要关注生成模型，还要关注信息选择、检索质量、版本规则和执行日志。

这些实验使用小规模虚构数据，每组只运行了少量次数，能够说明机制，但不能代表生产系统的稳定性。后续还需要继续比较关键词检索与语义检索、文档切分、`top_k`、重排和 RAG 评估。

## 6. 文件说明

| 文件 | 内容 |
| --- | --- |
| [context_selection.py](context_selection.py) | 对比完整历史与截断历史 |
| [memory_conflict_experiment.py](memory_conflict_experiment.py) | 记忆冲突更新与跨会话读取 |
| [rag_first_experiment.py](rag_first_experiment.py) | 无 RAG / 有 RAG 对照 |
| [rag_conflict_experiment.py](rag_conflict_experiment.py) | 新旧文档冲突与新鲜度规则 |
| [results/context_compression](results/context_compression/) | 六种上下文压缩策略的实际 JSON 结果 |
| [results/experiment_outputs.md](results/experiment_outputs.md) | Memory 与 RAG 的关键实际输出摘录 |

代码不包含 API Key；运行时从环境变量、本地 `.env` 或隐藏输入中读取密钥。
