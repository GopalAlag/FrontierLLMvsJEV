"""Confidence-gated routing: classifier output -> servicing workflow or live agent."""
from __future__ import annotations

from dataclasses import dataclass

from .intents import AGENT, BY_NAME
from .workflows import Result, service

LOW_CONF = "low_confidence_escalation"


@dataclass
class Decision:
    action: str           # workflow | agent
    workflow: str         # workflow id or AGENT
    reason: str
    result: Result | None = None


def route(intent: str, confidence: float, threshold: float, xml: str, error: str | None = None) -> Decision:
    if error or intent not in BY_NAME:
        return Decision("agent", AGENT, "classifier_error" if error else "invalid_label")
    wf = BY_NAME[intent].workflow
    if wf == AGENT:
        return Decision("agent", AGENT, "caller_requested_agent", service(intent, xml))
    if confidence < threshold:
        return Decision("agent", AGENT, LOW_CONF)
    return Decision("workflow", wf, "confident", service(intent, xml))


def expected(true_intent: str) -> tuple[str, str]:
    """(action, workflow) a perfect classifier would produce for the caller's true intent."""
    wf = BY_NAME[true_intent].workflow
    return ("agent" if wf == AGENT else "workflow"), wf
