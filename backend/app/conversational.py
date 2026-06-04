"""
conversational.py — Conversational Analytics (Gemini Data Analytics) bridge for
"Ask UBS". Streams a natural-language question to the published BigQuery data
agent and yields UI blocks **as they arrive** (true streaming), so the frontend
shows live thinking progress instead of waiting for the whole answer.

Block dicts yielded (match the Ask UBS frontend):
    {"type": "thinking", "text": ...}    progress breadcrumb (agent reasoning)
    {"type": "text",     "text": ...}    final narrative answer (markdown)
    {"type": "sql",      "sql": ...}     the generated BigQuery SQL
    {"type": "table",    "columns": [...], "rows": [[...]]}
    {"type": "chart",    "spec": {mark,x,y,title}, "vega": <vega-lite spec>}

The agent (display name UBS_POV) already carries schema, synonyms, joins and
example queries, so we only pass the question.
"""
from __future__ import annotations

from typing import Dict, Iterator, List, Tuple

from google.cloud import geminidataanalytics as gda
from google.protobuf.json_format import MessageToDict

from .config import settings


def _parent() -> str:
    return f"projects/{settings.GOOGLE_CLOUD_PROJECT}/locations/{settings.CA_LOCATION}"


def _agent_name() -> str:
    return f"{_parent()}/dataAgents/{settings.CA_AGENT_ID}"


def _to_py(value):
    """Recursively convert proto Struct / ListValue / Value into plain python."""
    try:
        from google.protobuf.struct_pb2 import Struct, ListValue, Value
    except Exception:  # pragma: no cover
        Struct = ListValue = Value = ()  # type: ignore
    pb = getattr(value, "_pb", value)
    if isinstance(pb, Struct):
        return MessageToDict(pb)
    if isinstance(pb, ListValue):
        return [_to_py(v) for v in pb.values]
    if isinstance(pb, Value):
        kind = pb.WhichOneof("kind")
        if kind == "struct_value":
            return _to_py(pb.struct_value)
        if kind == "list_value":
            return _to_py(pb.list_value)
        if kind == "number_value":
            return pb.number_value
        if kind == "string_value":
            return pb.string_value
        if kind == "bool_value":
            return pb.bool_value
        return None
    if hasattr(value, "items"):
        return {k: _to_py(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_py(v) for v in value]
    return value


def _result_rows(result) -> Tuple[List[str], List[List]]:
    columns: List[str] = [getattr(f, "name", "") for f in (getattr(getattr(result, "schema", None), "fields", []) or [])]
    rows: List[List] = []
    for item in getattr(result, "data", []) or []:
        d = _to_py(item)
        if isinstance(d, dict):
            if not columns:
                columns = list(d.keys())
            rows.append([d.get(c) for c in columns])
        elif isinstance(d, list):
            rows.append(d)
        else:
            rows.append([d])
    return columns, rows


def _clarification_text(cm) -> str:
    """Flatten a ClarificationMessage's questions into a single prompt string."""
    parts: List[str] = []
    for q in getattr(cm, "questions", []) or []:
        if isinstance(q, str):
            parts.append(q)
        else:
            qp = getattr(q, "parts", None)
            parts.append("".join(qp) if qp else (getattr(q, "text", None) or str(q)))
    return " ".join(p.strip() for p in parts if p).strip()


def _process(sm, seen_sql: set) -> Iterator[Dict]:
    """Translate one streamed SystemMessage into UI block dicts. Emits a
    {"type":"clarification"} block when the agent asks a question (typed
    ClarificationMessage) so the caller can keep a human in the loop."""
    which = sm._pb.WhichOneof("kind") if hasattr(sm, "_pb") else None

    if which == "text":
        tmsg = sm.text
        ttype = getattr(tmsg, "text_type", None)
        tval = int(ttype) if ttype is not None else None
        parts = [p for p in (getattr(tmsg, "parts", []) or [])]
        if tval == 1:  # FINAL_RESPONSE
            text = "".join(parts).strip()
            if text:
                yield {"type": "text", "text": text}
        elif tval == 3:  # FOLLOWUP_QUESTIONS
            fups = [p.strip() for p in parts if p.strip()]
            if fups:
                yield {"type": "text", "text": "**Suggested follow-ups:** " + "  ·  ".join(fups)}
        else:  # THOUGHT / unspecified -> progress breadcrumb
            label = (parts[0] if parts else "").strip()
            if label:
                yield {"type": "thinking", "text": label[:140]}

    elif which == "data":
        data = sm.data
        sql = getattr(data, "generated_sql", "") or ""
        if sql and sql not in seen_sql:
            seen_sql.add(sql)
            yield {"type": "thinking", "text": "Generated BigQuery SQL — running it…"}
            yield {"type": "sql", "sql": sql}
        result = getattr(data, "result", None)
        if result is not None:
            columns, rows = _result_rows(result)
            if columns and rows:
                yield {"type": "table", "columns": columns, "rows": rows}

    elif which == "chart":
        result = getattr(sm.chart, "result", None)
        spec = None
        if result is not None:
            pb = getattr(result, "_pb", None)
            if pb is not None and pb.HasField("vega_config"):
                spec = MessageToDict(pb.vega_config)
        if spec:
            enc = spec.get("encoding", {})
            yield {"type": "chart",
                   "spec": {"mark": spec.get("mark", "bar"),
                            "x": (enc.get("x") or {}).get("field"),
                            "y": (enc.get("y") or {}).get("field"),
                            "title": spec.get("title")},
                   "vega": spec}

    elif which == "clarification":
        ctext = _clarification_text(sm.clarification)
        if ctext:
            yield {"type": "clarification", "text": ctext}

    elif which == "schema":
        yield {"type": "thinking", "text": "Resolved the schema for your question…"}
    elif which == "analysis":
        yield {"type": "thinking", "text": "Analysing the data to answer…"}
    elif which == "error":
        err = sm.error
        yield {"type": "text", "text": f"The data agent reported: {getattr(err, 'text', None) or str(err)}"}


def ask_conversational(question: str) -> Iterator[Dict]:
    """Single-shot: stream a question to the CA data agent, yielding UI blocks."""
    client = gda.DataChatServiceClient()
    request = gda.ChatRequest(
        parent=_parent(),
        data_agent_context=gda.DataAgentContext(data_agent=_agent_name()),
        messages=[gda.Message(user_message=gda.UserMessage(text=question))],
    )
    seen_sql: set = set()
    for reply in client.chat(request=request):
        sm = getattr(reply, "system_message", None)
        if sm is not None:
            yield from _process(sm, seen_sql)


# ---------------------------------------------------------------------------
# Multi-turn (human-in-the-loop) conversations — for clarification resolution
# ---------------------------------------------------------------------------
def start_conversation() -> str:
    """Create a stateful CA conversation bound to the agent; return its name."""
    import uuid as _uuid
    client = gda.DataChatServiceClient()
    conv = gda.Conversation(agents=[_agent_name()])
    created = client.create_conversation(
        parent=_parent(), conversation_id=f"ubs-{_uuid.uuid4().hex[:12]}", conversation=conv)
    return created.name


def converse(conversation_name: str, question: str) -> Iterator[Dict]:
    """Send one turn into an existing conversation (service keeps the history),
    so the agent can resolve a clarification with the user's reply."""
    client = gda.DataChatServiceClient()
    request = gda.ChatRequest(
        parent=_parent(),
        conversation_reference=gda.ConversationReference(
            conversation=conversation_name,
            data_agent_context=gda.DataAgentContext(data_agent=_agent_name()),
        ),
        messages=[gda.Message(user_message=gda.UserMessage(text=question))],
    )
    seen_sql: set = set()
    for reply in client.chat(request=request):
        sm = getattr(reply, "system_message", None)
        if sm is not None:
            yield from _process(sm, seen_sql)
