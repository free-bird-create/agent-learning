"""Small end-to-end RAG experiment: direct LLM vs retrieved context + LLM."""

from __future__ import annotations

import os
import sys
from getpass import getpass
from pathlib import Path

from dotenv import dotenv_values
from openai import OpenAI


SPARSE_DIR = Path(
    r"D:\agent\projects\ai-agent-book-proxy\chapter3\sparse-embedding"
)
CHAPTER2_ENV = Path(
    r"D:\agent\projects\ai-agent-book-proxy\chapter2\context-compression\.env"
)

sys.path.insert(0, str(SPARSE_DIR))

from bm25_engine import SparseSearchEngine  # noqa: E402


DOCUMENTS = [
    {
        "doc_id": "nova_schedule",
        "text": (
            "The NOVA-17 weekly review starts at 14:30 every Tuesday in room B305. "
            "Every participant must bring a blue access card."
        ),
    },
    {
        "doc_id": "orion_schedule",
        "text": (
            "The ORION-8 weekly review starts at 09:00 every Friday in room C210. "
            "Every participant must bring a red access card."
        ),
    },
    {
        "doc_id": "nova_compute",
        "text": (
            "The NOVA-17 project uses compute cluster A7 for nightly training jobs. "
            "Jobs should be submitted before 22:00."
        ),
    },
]

QUESTION = "NOVA-17 的每周例会在什么时间、什么地点，需要携带什么？"
SEARCH_QUERY = "NOVA-17 weekly review time room access card"


def load_client() -> tuple[OpenAI, str]:
    env = dotenv_values(CHAPTER2_ENV) if CHAPTER2_ENV.exists() else {}
    api_key = os.getenv("DEEPSEEK_API_KEY") or env.get("DEEPSEEK_API_KEY")
    model = os.getenv("MODEL_NAME") or env.get("MODEL_NAME") or "deepseek-flash"
    if not api_key:
        api_key = getpass("DeepSeek API Key: ")
    if not api_key:
        raise RuntimeError("DeepSeek API Key is required")
    client = OpenAI(
        api_key=str(api_key),
        base_url="https://api.deepseek.com",
        timeout=60.0,
        max_retries=0,
    )
    return client, str(model)


def ask(client: OpenAI, model: str, system: str, user: str) -> str:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        max_tokens=256,
        extra_body={"thinking": {"type": "disabled"}},
    )
    return response.choices[0].message.content or "<empty response>"


def build_retriever() -> SparseSearchEngine:
    engine = SparseSearchEngine()
    engine.index_batch([
        {
            "doc_id": doc["doc_id"],
            "text": doc["text"],
            "metadata": {},
        }
        for doc in DOCUMENTS
    ])
    return engine


def main() -> None:
    client, model = load_client()

    print("=== 1. 问题 ===")
    print(QUESTION)

    direct_answer = ask(
        client,
        model,
        "只根据当前消息提供的信息回答；没有依据就明确说不知道，不要猜。",
        QUESTION,
    )
    print("\n=== 2. 不使用 RAG 的回答 ===")
    print(direct_answer)

    engine = build_retriever()
    results = engine.search(SEARCH_QUERY, top_k=2)

    print("\n=== 3. Retrieval 检索结果 ===")
    for rank, result in enumerate(results, 1):
        print(f"#{rank} {result['doc_id']} score={result['score']:.10f}")
        print("matched_terms:", result["debug"]["matched_terms"])
        print(result["text"])

    context = "\n\n".join(
        f"[{result['doc_id']}] {result['text']}"
        for result in results
    )
    augmented_question = f"""请只根据下面检索到的资料回答，并引用来源 doc_id。

检索资料：
{context}

问题：{QUESTION}
"""
    rag_answer = ask(
        client,
        model,
        "你是基于检索资料回答问题的助手。资料没有说明的内容不得猜测。",
        augmented_question,
    )

    print("\n=== 4. 使用 RAG 的回答 ===")
    print(rag_answer)

    print("\n=== 5. 本次数据流 ===")
    print("问题 -> BM25 检索 -> 取回相关文档 -> 拼入 Context -> DeepSeek 生成答案")


if __name__ == "__main__":
    main()
