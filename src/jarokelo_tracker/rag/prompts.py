def build_prompt(context: str, query: str) -> str:
    return (
        "You are a civic assistant. Answer the question only with information from "
        "the retrieved issues. If the answer is unknown, say so. Always include "
        "issue IDs and URLs when relevant. Keep the answer factual, concise, and "
        "without extra commentary.\n\n"
        f"Context:\n---\n{context}\n---\n\n"
        f"Question:\n{query}\n"
    )
