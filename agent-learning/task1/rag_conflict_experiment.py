"""RAG experiment: retrieval finds conflicting old and new notices."""

from __future__ import annotations

from rag_first_experiment import SparseSearchEngine, ask, load_client


DOCUMENTS = [
    {
        "doc_id": "nova_schedule_2026_08_20",
        "publication_date": "2026-08-20",
        "text": (
            "The NOVA-17 weekly review starts at 10:00 every Monday in room B201. "
            "Every participant must bring a green access card."
        ),
    },
    {
        "doc_id": "nova_schedule_2026_09_18",
        "publication_date": "2026-09-18",
        "text": (
            "The NOVA-17 weekly review starts at 16:00 every Thursday in room D402. "
            "Every participant must bring a yellow access card."
        ),
    },
    {
        "doc_id": "nova_compute",
        "publication_date": "2026-09-10",
        "text": "The NOVA-17 project uses compute cluster A7 for nightly training jobs.",
    },
    {
        "doc_id": "lab_safety",
        "publication_date": "2026-09-11",
        "text": "Laboratory visitors must wear protective glasses in the hardware area.",
    },
    {
        "doc_id": "travel_policy",
        "publication_date": "2026-09-12",
        "text": "Conference travel expenses require approval before tickets are purchased.",
    },
    {
        "doc_id": "inventory_notice",
        "publication_date": "2026-09-13",
        "text": "New keyboards and monitors have been added to the equipment inventory.",
    },
]

QUESTION = "NOVA-17 当前的每周例会在什么时间、什么地点，需要携带什么？"
SEARCH_QUERY = "NOVA-17 weekly review time room access card"


def build_retriever() -> SparseSearchEngine:
    engine = SparseSearchEngine()
    engine.index_batch([
        {
            "doc_id": doc["doc_id"],
            "text": doc["text"],
            "metadata": {"publication_date": doc["publication_date"]},
        }
        for doc in DOCUMENTS
    ])
    return engine


def build_context(results: list[dict]) -> str:
    return "\n\n".join(
        (
            f"[{result['doc_id']}] "
            f"publication_date={result['metadata']['publication_date']}\n"
            f"{result['text']}"
        )
        for result in results
    )


def main() -> None:
    client, model = load_client()
    engine = build_retriever()
    results = engine.search(SEARCH_QUERY, top_k=2)

    print("=== 1. 检索结果：检索器只负责找相关文档 ===")
    for rank, result in enumerate(results, 1):
        print(
            f"#{rank} {result['doc_id']} "
            f"date={result['metadata']['publication_date']} "
            f"score={result['score']:.6f}"
        )
        print("matched_terms:", result["debug"]["matched_terms"])
        print(result["text"])

    context = build_context(results)
    user_message = f"""检索资料：
{context}

问题：{QUESTION}
"""

    naive_answer = ask(
        client,
        model,
        (
            "只根据检索资料回答。资料存在冲突时，不要自行假定哪条有效，"
            "请明确指出冲突并引用 doc_id。"
        ),
        user_message,
    )
    print("\n=== 2. 普通 RAG：没有规定如何处理新旧冲突 ===")
    print(naive_answer)

    freshness_answer = ask(
        client,
        model,
        (
            "只根据检索资料回答。同一事实出现冲突时，比较 publication_date，"
            "采用发布日期最新的公告，并引用 doc_id 和发布日期。"
        ),
        user_message,
    )
    print("\n=== 3. 加入新鲜度规则后的 RAG ===")
    print(freshness_answer)

    print("\n=== 4. 本次要观察 ===")
    print("BM25 能找到相关资料，但它本身不知道哪一份是当前有效版本。")
    print("版本日期进入 Context 后，还需要明确规则让 LLM 处理冲突。")


if __name__ == "__main__":
    main()
