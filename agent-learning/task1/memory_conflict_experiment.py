"""Controlled experiment for LLM-driven memory conflict handling.

The course code does not expose DeepSeek as a provider, so this script keeps
the original memory implementation and swaps only the API client at runtime.
All experiment data is isolated under results/memory_conflict.
"""

from __future__ import annotations

import os
import sys
from getpass import getpass
from pathlib import Path

from dotenv import dotenv_values
from openai import OpenAI


CHAPTER_DIR = Path(
    r"D:\agent\projects\ai-agent-book-proxy\chapter3\user-memory"
)
CHAPTER2_ENV = Path(
    r"D:\agent\projects\ai-agent-book-proxy\chapter2\context-compression\.env"
)
RESULT_DIR = Path(__file__).resolve().parent / "results" / "memory_conflict"

sys.path.insert(0, str(CHAPTER_DIR))

from background_memory_processor import (  # noqa: E402
    BackgroundMemoryProcessor,
    MemoryProcessorConfig,
)
from config import Config, MemoryMode  # noqa: E402
from conversational_agent import ConversationConfig, ConversationalAgent  # noqa: E402
from memory_manager import create_memory_manager  # noqa: E402


class DeepSeekClientAdapter:
    """Expose the API shape used by the course and disable thinking mode."""

    class _Completions:
        def __init__(self, delegate):
            self._delegate = delegate

        def create(self, *args, **kwargs):
            kwargs.setdefault("extra_body", {"thinking": {"type": "disabled"}})
            return self._delegate.create(*args, **kwargs)

    class _Chat:
        def __init__(self, delegate):
            self.completions = DeepSeekClientAdapter._Completions(
                delegate.completions
            )

    def __init__(self, api_key: str):
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            timeout=60.0,
            max_retries=0,
        )
        self.chat = self._Chat(client.chat)


def load_deepseek_config() -> tuple[str, str]:
    env = dotenv_values(CHAPTER2_ENV) if CHAPTER2_ENV.exists() else {}
    api_key = os.getenv("DEEPSEEK_API_KEY") or env.get("DEEPSEEK_API_KEY")
    model = os.getenv("MODEL_NAME") or env.get("MODEL_NAME") or "deepseek-flash"

    if not api_key:
        api_key = getpass("DeepSeek API Key: ")
    if not api_key:
        raise RuntimeError("DeepSeek API Key is required")

    return str(api_key), str(model)


def print_memories(title: str, manager) -> None:
    manager.load_memory()
    print(f"\n=== {title} ===")
    print(manager.get_context_string())


def main() -> None:
    api_key, model = load_deepseek_config()

    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    Config.MEMORY_STORAGE_DIR = str(RESULT_DIR / "memories")
    Config.CONVERSATION_HISTORY_DIR = str(RESULT_DIR / "conversations")
    Config.create_directories()

    user_id = "memory_conflict_demo"
    memory_file = Path(Config.MEMORY_STORAGE_DIR) / f"{user_id}_memory.json"
    if memory_file.exists():
        memory_file.unlink()

    manager = create_memory_manager(user_id, MemoryMode.NOTES)
    old_id = manager.add_memory(
        content="用户主要使用 Windows。",
        session_id="seed-session",
        tags=["operating_system"],
    )
    print_memories("1. 初始记忆", manager)

    processor = BackgroundMemoryProcessor(
        user_id=user_id,
        api_key=api_key,
        provider="kimi",  # Constructor placeholder; client is replaced below.
        model=model,
        config=MemoryProcessorConfig(
            conversation_interval=1,
            min_conversation_turns=1,
            context_window=10,
            output_operations=True,
        ),
        memory_mode=MemoryMode.NOTES,
        verbose=True,
    )
    processor.analysis_agent.provider = "deepseek"
    processor.analysis_agent.model = model
    processor.analysis_agent.client = DeepSeekClientAdapter(api_key)

    new_conversation = [
        {
            "role": "user",
            "content": "更正一下：我现在主要使用 Linux，已经不再把 Windows 作为主要系统。",
        },
        {
            "role": "assistant",
            "content": "明白了，你现在主要使用 Linux。",
        },
    ]

    print("\n=== 2. 交给记忆分析 Agent 的新对话 ===")
    for message in new_conversation:
        print(f"{message['role']}: {message['content']}")

    processor.analyze_conversation(new_conversation)

    print("\n=== 3. 模型产生的工具调用 ===")
    calls = processor.analysis_agent.tool_calls
    if not calls:
        print("没有产生工具调用")
    for index, call in enumerate(calls, 1):
        print(f"工具 {index}: {call.tool_name}")
        print(f"参数: {call.arguments}")
        print(f"结果: {call.result or call.error}")

    final_manager = create_memory_manager(user_id, MemoryMode.NOTES)
    print_memories("4. 更新后的记忆", final_manager)

    os_notes = [
        note for note in final_manager.notes
        if "operating_system" in note.tags
    ]
    updated_in_place = (
        len(os_notes) == 1
        and os_notes[0].note_id == old_id
        and "Linux" in os_notes[0].content
    )

    print("\n=== 5. 实验判断 ===")
    if updated_in_place:
        print("PASS: 模型调用 update_memory，并在原 Note 上完成了更新。")
    elif len(os_notes) > 1:
        print("OBSERVE: 模型新增了另一条记忆，产生了 Windows/Linux 冲突。")
    else:
        print("OBSERVE: 结果不是预期更新，请结合上面的工具调用分析原因。")
    print(f"实验文件: {memory_file}")

    print("\n=== 6. 全新会话读取长期记忆 ===")
    reader = ConversationalAgent(
        user_id=user_id,
        api_key=api_key,
        provider="kimi",  # Constructor placeholder; client is replaced below.
        model=model,
        config=ConversationConfig(
            enable_memory_context=True,
            enable_conversation_history=False,
        ),
        memory_mode=MemoryMode.NOTES,
        verbose=True,
    )
    reader.provider = "deepseek"
    reader.model = model
    reader.client = DeepSeekClientAdapter(api_key)

    print(f"新会话 ID: {reader.get_session_id()}")
    question = "只根据你保存的用户记忆回答：我目前主要使用什么操作系统？"
    print(f"用户问题: {question}")
    answer = reader.chat(question)
    print(f"\n跨会话回答: {answer}")


if __name__ == "__main__":
    main()
