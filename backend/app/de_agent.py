"""
de_agent.py — Bridge to the REAL Google Cloud Data Engineering Agent.

This is the genuine Google product (not a simulation): a BigQuery + Dataform ELT
expert exposed as an A2A agent at a fixed tenant path on
geminidataanalytics.googleapis.com. It operates on a Dataform workspace
(the required `gcpresource` A2A extension) — here, our live repository
`fsi_pov_pipeline` / workspace `dev`.

`de_agent_messages()` sends an instruction over the A2A `message:stream`
endpoint and returns the agent's streamed ROLE_AGENT messages (its real
reasoning + answer) plus the conversation token for multi-turn use.
"""
from __future__ import annotations

import json
import urllib.request
import uuid
from typing import Optional

import google.auth
import google.auth.transport.requests as gart

from .config import settings

_HOST = "https://geminidataanalytics.googleapis.com/v1/a2a"
_GCP_RES_EXT = "https://geminidataanalytics.googleapis.com/a2a/extensions/gcpresource/v1"
_TOKEN_EXT = "https://geminidataanalytics.googleapis.com/a2a/extensions/conversationtoken/v1"
_LEVEL_EXT = "https://geminidataanalytics.googleapis.com/a2a/extensions/messagelevel/v1"


def _token() -> str:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(gart.Request())
    return creds.token


def _resource() -> str:
    return (f"projects/{settings.GOOGLE_CLOUD_PROJECT}/locations/{settings.DE_AGENT_LOCATION}"
            f"/repositories/{settings.DATAFORM_REPO}/workspaces/{settings.DATAFORM_WORKSPACE}")


def workspace_url() -> str:
    return (f"https://console.cloud.google.com/bigquery/dataform/locations/"
            f"{settings.DE_AGENT_LOCATION}/repositories/{settings.DATAFORM_REPO}"
            f"/workspaces/{settings.DATAFORM_WORKSPACE}?project={settings.GOOGLE_CLOUD_PROJECT}")


def de_agent_messages(prompt: str, conversation_token: Optional[str] = None,
                      timeout: int = 200) -> dict:
    """Call the real DE agent; return {messages: [text...], token: str|None}."""
    loc = settings.DE_AGENT_LOCATION
    url = (f"{_HOST}/projects/{settings.GOOGLE_CLOUD_PROJECT}/locations/{loc}"
           f"/agents/dataengineeringagent/v1/message:stream")
    metadata: dict = {_GCP_RES_EXT: {"gcpResourceId": _resource()}}
    if conversation_token:
        metadata[_TOKEN_EXT] = conversation_token
    body = {
        "request": {
            "messageId": str(uuid.uuid4()),
            "role": "ROLE_USER",
            "content": [{"text": prompt}],
        },
        "metadata": metadata,
    }
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": f"Bearer {_token()}",
                 "Content-Type": "application/json",
                 "X-A2A-Extensions": _GCP_RES_EXT})
    raw = urllib.request.urlopen(req, timeout=timeout).read().decode()
    events = json.loads(raw)

    messages: list[str] = []
    token: Optional[str] = None
    for ev in events:
        su = ev.get("statusUpdate") or {}
        status = su.get("status") or {}
        msg = status.get("message") or {}
        if msg.get("role") == "ROLE_AGENT":
            for part in msg.get("content", []) or []:
                t = part.get("text")
                if t:
                    messages.append(t)
        if su.get("final"):
            token = (su.get("metadata") or {}).get(_TOKEN_EXT)
    return {"messages": messages, "token": token}
