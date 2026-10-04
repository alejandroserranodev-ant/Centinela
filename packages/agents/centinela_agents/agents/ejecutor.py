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
from centinela_agents.tools import ToolRegistry

logger = logging.getLogger(__name__)


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

    try:
        if action_type == "email_draft":
            return _execute_email_draft(
                provider,
                action_id,
                parameters,
                email_tool
            )
        elif action_type == "task":
            return _execute_task(action_id, parameters, task_tool)
        elif action_type == "purchase_order_draft":
            return _execute_po_draft(action_id, parameters, po_tool)
        elif action_type == "price_change_draft":
            return _execute_price_draft(action_id, parameters, price_tool)
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    except Exception as e:
        logger.error(f"Ejecutor: execution failed: {e}")
        return {
            "executed_action": None,
        }


def _execute_email_draft(
    provider: LLMProvider,
    action_id: str,
    parameters: dict[str, Any],
    email_tool: Any,
) -> dict[str, Any]:
    """Execute email_draft: LLM writes body, tool creates draft."""
    recipient = parameters.get("recipient")
    vendedor_id = parameters.get("vendedor_id")

    prompt = f"""Redacta el cuerpo de un email según FIN-POL-004 §6.

PARÁMETROS:
- Destinatario: {recipient}
- Vendedor: {vendedor_id}

REGLAS:
1. Cortés, redactado, firmado por vendedor
2. No uses nombres reales (están enmascarados como IDs)
3. Refiere los parámetros por sus placeholders
4. Tono profesional
5. Máximo 200 palabras

Redacta SOLO el cuerpo del email. Sin subject, sin saludos formales iniciales."""

    try:
        response = provider.generate_text(
            LLMRequest(
                system_prompt="Redactas emails profesionales en español para clientes.",
                user_prompt=prompt,
                temperature=0.0,
                thinking=False,
            )
        )

        body = response.text.strip()

        if email_tool:
            draft_result = email_tool.execute(
                recipient=recipient,
                body=body,
            )
            executed = ExecutedAction(
                actionId=action_id,
                type="email_draft",
                result=body,
                parameters=parameters,
            )
        else:
            executed = ExecutedAction(
                actionId=action_id,
                type="email_draft",
                result=body,
                parameters=parameters,
            )

        logger.info(f"Ejecutor: email draft created for {recipient}")
        return {
            "executed_action": executed.model_dump(),
        }

    except Exception as e:
        logger.error(f"Ejecutor: email draft failed: {e}")
        raise


def _execute_task(
    action_id: str,
    parameters: dict[str, Any],
    task_tool: Any,
) -> dict[str, Any]:
    """Execute task: code creates manual task."""
    owner = parameters.get("owner")
    cliente_id = parameters.get("cliente_id")

    logger.info(f"Ejecutor: creating task for {owner} on {cliente_id}")

    if task_tool:
        task_result = task_tool.execute(
            owner=owner,
            title=f"Revisar cliente {cliente_id}",
            description=f"Acción manual requerida para {cliente_id}",
        )
        result_data = {
            "task_id": task_result.task_id,
            "owner": owner,
        }
    else:
        result_data = {"owner": owner, "description": "Tarea manual"}

    executed = ExecutedAction(
        actionId=action_id,
        type="task",
        result=result_data,
        parameters=parameters,
    )

    return {
        "executed_action": executed.model_dump(),
    }


def _execute_po_draft(
    action_id: str,
    parameters: dict[str, Any],
    po_tool: Any,
) -> dict[str, Any]:
    """Execute purchase_order_draft: code creates PO draft."""
    proveedor_id = parameters.get("proveedor_id")
    sku = parameters.get("sku")
    quantity = parameters.get("units")
    warehouse = parameters.get("warehouse")

    logger.info(f"Ejecutor: creating PO for {proveedor_id} {sku} x{quantity}")

    if po_tool:
        po_result = po_tool.execute(
            proveedor_id=proveedor_id,
            sku=sku,
            quantity=quantity,
            warehouse=warehouse,
        )
        result_data = {
            "order_id": po_result.order_id,
            "proveedor": proveedor_id,
            "sku": sku,
            "quantity": quantity,
        }
    else:
        result_data = {"proveedor": proveedor_id, "sku": sku}

    executed = ExecutedAction(
        actionId=action_id,
        type="purchase_order_draft",
        result=result_data,
        parameters=parameters,
    )

    return {
        "executed_action": executed.model_dump(),
    }


def _execute_price_draft(
    action_id: str,
    parameters: dict[str, Any],
    price_tool: Any,
) -> dict[str, Any]:
    """Execute price_change_draft: code creates price change draft."""
    sku = parameters.get("sku")
    linea = parameters.get("linea")
    price_increase_pct = parameters.get("price_increase_pct")

    logger.info(f"Ejecutor: creating price change {sku or linea} +{price_increase_pct}%")

    if price_tool:
        price_result = price_tool.execute(
            sku=sku,
            linea=linea,
            price_increase_pct=price_increase_pct,
        )
        result_data = {
            "change_id": price_result.change_id,
            "increase_pct": price_increase_pct,
        }
    else:
        result_data = {"increase_pct": price_increase_pct}

    executed = ExecutedAction(
        actionId=action_id,
        type="price_change_draft",
        result=result_data,
        parameters=parameters,
    )

    return {
        "executed_action": executed.model_dump(),
    }
