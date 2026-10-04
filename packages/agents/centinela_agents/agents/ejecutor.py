"""
Ejecutor: Execute an approved action.

Receives approved action (with decision recorded) and executes it.
For email_draft: LLM writes body (thinking OFF, data pre-masked).
For other types: code creates draft/task.

Input: approved action, decision
Output: ExecutedAction
Tools: none for LLM (action tools in code)
Model: LLM thinking OFF (only for email body, minimal reasoning)
"""

import logging
from typing import Any

from centinela_agents.llm_provider import (
    LLMProvider,
    LLMRequest,
)
from centinela_agents.schema import ExecutedAction
from centinela_agents.security import mask_data
from centinela_agents.skills import skill
from centinela_agents.tools import ToolRegistry

logger = logging.getLogger(__name__)

EMAIL_TOKENS = 400


class EjecutorError(Exception):
    """Ejecutor step error."""
    pass


def execute_action(
    provider: LLMProvider,
    action: dict[str, Any],
    decision: dict[str, Any],
    tools: ToolRegistry,
) -> dict[str, Any]:
    """
    Execute an approved action.

    Args:
        provider: LLM provider (thinking OFF)
        action: {
            id: str,
            title: str,
            description: str,
            type: str,  # email_draft, task, purchase_order_draft, price_change_draft
            parameters: dict,
            impact: Figure | None,
        }
        decision: {
            kind: "approve" | "edit",
            actionId: str,
            parameters: dict (if kind="edit"),
        }
        tools: ToolRegistry with action tools

    Returns:
        {
            executed_action: ExecutedAction,
        }

    Rules:
        1. Check action.type: if email_draft, call LLM to write body
        2. For other types: use action tools in code (no LLM)
        3. LLM for email: data is PRE-MASKED (no sensitive info)
        4. Parameters are immutable (from decision, never chosen by LLM)
        5. Return ExecutedAction with draft/task
        6. Idempotent: alert_id + action_id + decision_id = unique key
    """
    action_id = action.get("id")
    action_type = action.get("type")
    parameters = decision.get("parameters") or action.get("parameters", {})

    logger.info(
        f"Ejecutor: execute {action_type} action {action_id}",
        extra={"action_type": action_type, "action_id": action_id}
    )

    email_tool = tools.email_draft if hasattr(tools, 'email_draft') else None
    task_tool = tools.task if hasattr(tools, 'task') else None
    po_tool = tools.purchase_order_draft if hasattr(tools, 'purchase_order_draft') else None
    price_tool = tools.price_change_draft if hasattr(tools, 'price_change_draft') else None

    if action_type == "email_draft":
        return _execute_email_draft(provider, action, parameters, email_tool)
    if action_type == "task":
        return _execute_task(action, parameters, task_tool)
    if action_type == "purchase_order_draft":
        return _execute_po_draft(action_id, parameters, po_tool)
    if action_type == "price_change_draft":
        return _execute_price_draft(action_id, parameters, price_tool)
    raise ValueError(f"Unknown action type: {action_type}")


def _executed(action_id: str, action_type: str, result: str, parameters: dict[str, Any]) -> dict[str, Any]:
    executed = ExecutedAction(actionId=action_id, type=action_type, result=result, parameters=parameters)
    return {"executed_action": executed.model_dump()}


def _execute_email_draft(
    provider: LLMProvider,
    action: dict[str, Any],
    parameters: dict[str, Any],
    email_tool: Any,
) -> dict[str, Any]:
    recipient = parameters.get("recipient")
    listed = "\n".join(f"- {name}: {value}" for name, value in parameters.items())
    prompt = mask_data(f"""action.title: {action.get("title")}
action.description: {action.get("description")}
action.parameters:
{listed}

Escribe solo el cuerpo del correo, en español.""")
    response = provider.generate_text(
        LLMRequest(
            system_prompt=skill("ejecutor", "contrato", "plantillas"),
            user_prompt=prompt,
            temperature=0.0,
            max_tokens=EMAIL_TOKENS,
            thinking=False,
        )
    )
    body = response.text.strip()
    if email_tool:
        email_tool.execute(recipient=recipient, body=body)
    logger.info("Ejecutor: email draft created for %s", recipient)
    header = f"Borrador de correo para {recipient} guardado" if recipient else "Borrador de correo guardado"
    return _executed(action.get("id"), "email_draft", f"{header}: {body}", parameters)


def _execute_task(
    action: dict[str, Any],
    parameters: dict[str, Any],
    task_tool: Any,
) -> dict[str, Any]:
    owner = parameters.get("owner")
    title = action.get("title") or "Tarea manual"
    logger.info("Ejecutor: creating task %s for %s", title, owner)
    if task_tool:
        task_tool.execute(owner=owner, title=title, description=action.get("description"), parameters=parameters)
    result = f"Tarea «{title}» creada para {owner}." if owner else f"Tarea «{title}» creada, sin responsable asignado."
    return _executed(action.get("id"), "task", result, parameters)


def _execute_po_draft(
    action_id: str,
    parameters: dict[str, Any],
    po_tool: Any,
) -> dict[str, Any]:
    proveedor_id = parameters.get("proveedor_id")
    sku = parameters.get("sku")
    quantity = parameters.get("units")
    warehouse = parameters.get("warehouse")
    logger.info("Ejecutor: creating PO for %s %s x%s", proveedor_id, sku, quantity)
    if po_tool:
        po_tool.execute(proveedor_id=proveedor_id, sku=sku, quantity=quantity, warehouse=warehouse)
    words = [f"Borrador de orden de compra guardado: {quantity} unidades de {sku}"]
    if proveedor_id:
        words.append(f"al proveedor {proveedor_id}")
    if warehouse:
        words.append(f"para la bodega {warehouse}")
    return _executed(action_id, "purchase_order_draft", " ".join(words) + ".", parameters)


def _execute_price_draft(
    action_id: str,
    parameters: dict[str, Any],
    price_tool: Any,
) -> dict[str, Any]:
    sku = parameters.get("sku")
    linea = parameters.get("linea")
    price_increase_pct = parameters.get("price_increase_pct")
    logger.info("Ejecutor: creating price change %s +%s%%", sku or linea, price_increase_pct)
    if price_tool:
        price_tool.execute(sku=sku, linea=linea, price_increase_pct=price_increase_pct)
    target = f"del producto {sku}" if sku else f"de la línea {linea}"
    result = f"Borrador de cambio de precio {target} guardado: subir {price_increase_pct} %."
    return _executed(action_id, "price_change_draft", result, parameters)
