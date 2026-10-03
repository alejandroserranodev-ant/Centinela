"""
Agent implementations for Centinela orchestrator.

Each agent is a function that receives alert state, uses permitted tools,
calls the LLM with schema-constrained output, and returns typed result.

Agents:
- vigia: Detect rules broken, redact title (code + LLM thinking OFF)
- analista: Explain why alert happened (LLM thinking ON + tools)
- estratega: Propose 1-3 actions (LLM thinking ON + tools)
- ejecutor: Execute approved action (LLM thinking OFF for email body + code)
- orquestador: Classify rejection reason target (LLM thinking OFF)
"""
