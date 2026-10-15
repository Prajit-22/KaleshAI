"""Bounded document jobs and local-only exports. No network or model calls."""
from rag import Chunk

TASKS = {
    "Summary": "Summarize the selected document excerpts as short useful notes: main points, key facts and open questions. Cite exact source labels. If coverage is partial, say so first. Do not invent missing facts.",
    "Action items": "Extract action items explicitly supported by the selected document excerpts. Use a table: action, owner, deadline, source. Write 'not specified' for absent owners or dates. Distinguish explicit commitments from suggestions. If none exist, say so. If coverage is partial, say so first.",
}


def document_context(chunks: list[Chunk], budget: int = 14000):
    """Fit whole chunks in reading order, sampling across a large document."""
    if budget < 100:
        raise ValueError("budget must be at least 100")
    if not chunks:
        return "", [], "No readable document text."
    entries = [f"[{c.label}]\n{c.text}" for c in chunks]
    if sum(len(e) + 2 for e in entries) <= budget:
        chosen = list(range(len(chunks)))
    else:
        # Start, end and middle, then fill gaps evenly; never pretend this is exhaustive.
        priority = [0, len(chunks) - 1]
        spans = [(0, len(chunks) - 1)]
        while spans:
            lo, hi = spans.pop(0)
            mid = (lo + hi) // 2
            if mid not in priority:
                priority.append(mid)
            if mid - lo > 1:
                spans.append((lo, mid))
            if hi - mid > 1:
                spans.append((mid, hi))
        chosen, used = [], 0
        for i in dict.fromkeys(priority):
            size = len(entries[i]) + 2
            if used + size <= budget:
                chosen.append(i)
                used += size
        chosen.sort()
    selected = [chunks[i] for i in chosen]
    coverage = f"Using {len(selected)} of {len(chunks)} extracted chunks."
    if len(selected) < len(chunks):
        coverage += " Partial coverage: sampled excerpts, not a complete document review."
    else:
        coverage += " All extracted text included (upload limits still apply)."
    return "\n\n".join(entries[i] for i in chosen), [c.label for c in selected], coverage


def reply_export(message: dict) -> str:
    text = message["content"]
    if message.get("coverage"):
        text += "\n\nCoverage: " + message["coverage"]
    if message.get("sources"):
        text += "\n\nDocument excerpts supplied: " + ", ".join(message["sources"])
    if message.get("web"):
        text += "\n\nWeb sources:\n" + "\n".join(f"{i}. {r.title}: {r.url}" for i, r in enumerate(message["web"], 1))
    if message.get("web_note"):
        text += "\n\n" + message["web_note"]
    return text + "\n"


def conversation_export(messages: list[dict]) -> str:
    return "# KaleshAI conversation\n\n" + "\n\n".join(
        f"## {'You' if m['role'] == 'user' else 'KaleshAI'}\n\n{reply_export(m).strip()}" for m in messages
    ) + "\n"
