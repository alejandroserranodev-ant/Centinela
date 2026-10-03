"""
Action Tools: create drafts and tasks for approved actions.

Stub implementation. Real implementation requires:
- Database connection for idempotency key storage
- Integration with backend (API endpoints)
"""

import logging
import uuid
from typing import Any

from .tools import (
    EmailDraftResult,
    EmailDraftTool,
    PriceChangeDraftResult,
    PriceChangeDraftTool,
    PurchaseOrderDraftResult,
    PurchaseOrderDraftTool,
    TaskResult,
    TaskTool,
)

logger = logging.getLogger(__name__)


class EmailDraftStub(EmailDraftTool):
    """Stub implementation of email_draft tool."""

    def __init__(self):
        """Initialize stub."""
        self.draft_counter = 0

    def execute(
        self,
        recipient: str,
        body: str,
        subject: str | None = None,
        cc: list[str] | None = None,
    ) -> EmailDraftResult:
        """
        Create an email draft (not sent).

        Args:
            recipient: Cliente or proveedor ID
            body: Email body (pre-masked by Ejecutor)
            subject: Optional subject
            cc: CC list

        Returns:
            EmailDraftResult with draft ID
        """
        self.draft_counter += 1
        draft_id = f"email_draft_{uuid.uuid4().hex[:8]}"

        logger.info(
            f"Email draft created: {draft_id} to {recipient}",
            extra={"draft_id": draft_id, "recipient": recipient}
        )

        return EmailDraftResult(
            draft_id=draft_id,
            subject=subject or "Centinela",
            body=body,
            to=recipient,
            cc=cc or []
        )


class TaskStub(TaskTool):
    """Stub implementation of task tool."""

    def __init__(self):
        """Initialize stub."""
        self.task_counter = 0

    def execute(
        self,
        owner: str,
        title: str,
        description: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> TaskResult:
        """
        Create a task (manual action).

        Args:
            owner: Role (e.g., "Jefe de cartera")
            title: Task title
            description: Task description
            parameters: Additional parameters

        Returns:
            TaskResult with task ID
        """
        self.task_counter += 1
        task_id = f"task_{uuid.uuid4().hex[:8]}"

        logger.info(
            f"Task created: {task_id} for {owner}",
            extra={"task_id": task_id, "owner": owner}
        )

        return TaskResult(
            task_id=task_id,
            owner=owner,
            title=title,
            description=description
        )


class PurchaseOrderDraftStub(PurchaseOrderDraftTool):
    """Stub implementation of purchase_order_draft tool."""

    def __init__(self):
        """Initialize stub."""
        self.order_counter = 0

    def execute(
        self,
        proveedor_id: str,
        sku: str,
        quantity: int,
        warehouse: str,
    ) -> PurchaseOrderDraftResult:
        """
        Create a purchase order draft.

        Args:
            proveedor_id: Supplier ID
            sku: Product SKU
            quantity: Quantity (from calcular_impacto)
            warehouse: Destination warehouse

        Returns:
            PurchaseOrderDraftResult with order draft
        """
        self.order_counter += 1
        order_id = f"po_draft_{uuid.uuid4().hex[:8]}"

        logger.info(
            f"Purchase order draft created: {order_id}",
            extra={"order_id": order_id, "proveedor": proveedor_id, "sku": sku, "qty": quantity}
        )

        return PurchaseOrderDraftResult(
            order_id=order_id,
            proveedor_id=proveedor_id,
            sku=sku,
            quantity=quantity,
            warehouse=warehouse,
            estimated_arrival=None  # Stub: would calculate from supplier lead time
        )


class PriceChangeDraftStub(PriceChangeDraftTool):
    """Stub implementation of price_change_draft tool."""

    def __init__(self):
        """Initialize stub."""
        self.change_counter = 0

    def execute(
        self,
        sku: str | None = None,
        linea: str | None = None,
        price_increase_pct: float | None = None,
    ) -> PriceChangeDraftResult:
        """
        Create a price change draft.

        Args:
            sku: SKU to change (if SKU-level)
            linea: Line to change (if line-level)
            price_increase_pct: Percentage increase (from calcular_impacto)

        Returns:
            PriceChangeDraftResult with draft
        """
        if price_increase_pct is None:
            raise ValueError("price_increase_pct is required")

        self.change_counter += 1
        change_id = f"price_draft_{uuid.uuid4().hex[:8]}"

        logger.info(
            f"Price change draft created: {change_id}",
            extra={
                "change_id": change_id,
                "sku": sku,
                "linea": linea,
                "increase_pct": price_increase_pct
            }
        )

        return PriceChangeDraftResult(
            change_id=change_id,
            sku=sku,
            linea=linea,
            price_increase_pct=price_increase_pct,
            new_price=None  # Stub: would calculate from current list price
        )
