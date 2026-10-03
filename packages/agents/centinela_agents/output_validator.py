"""
Output Validator: Validates agent outputs using evals (schema, security, domain logic).

Integration point between agents and orchestrator.
"""

import logging
import re
from typing import Any

from pydantic import ValidationError

from .schema import (
    CauseIdentified,
    CauseNoEvidence,
    Action,
    ExecutedAction,
    Decision,
    RejectionClassifierOutput,
)

logger = logging.getLogger(__name__)


class OutputValidationError(Exception):
    """Raised when output fails validation."""

    def __init__(self, category: str, message: str, output: Any = None):
        self.category = category
        self.message = message
        self.output = output
        super().__init__(f"[{category}] {message}")


class OutputValidator:
    """Validates agent outputs at each stage."""

    def __init__(self, strict: bool = True):
        """
        Initialize validator.

        Args:
            strict: If True, fail on validation error.
                   If False, log warnings and continue.
        """
        self.strict = strict

    def validate_cause(self, output: dict[str, Any]) -> CauseIdentified | CauseNoEvidence | None:
        """Validate Analista output (Cause)."""
        try:
            if output.get("kind") == "identified":
                cause = CauseIdentified(**output)
            elif output.get("kind") == "no_evidence":
                cause = CauseNoEvidence(**output)
            else:
                raise OutputValidationError("schema", f"Invalid cause kind: {output.get('kind')}", output)
        except ValidationError as e:
            error = OutputValidationError("schema", f"Cause validation failed: {e}", output)
            if self.strict:
                raise error
            logger.warning(error)
            return None
        except OutputValidationError as error:
            if self.strict:
                raise
            logger.warning(error)
            return None

        # Security checks - only on text fields, not the dict
        try:
            if isinstance(cause, CauseIdentified):
                self._check_security(cause.sentence)
                for evidence in cause.evidence:
                    self._check_security(evidence.claim)
        except OutputValidationError as error:
            if self.strict:
                raise
            logger.warning(error)
            return None

        # Domain validation
        try:
            if isinstance(cause, CauseIdentified):
                assert len(cause.evidence) > 0, "Identified cause must have evidence"
                assert len(cause.sentence) > 5, "Sentence too short"
        except AssertionError as e:
            error = OutputValidationError("domain", str(e), output)
            if self.strict:
                raise error
            logger.warning(error)
            return None

        logger.info(f"Cause validated: kind={cause.kind}")
        return cause

    def validate_action(self, output: dict[str, Any]) -> Action | None:
        """Validate Estratega output (Action)."""
        try:
            action = Action(**output)
        except ValidationError as e:
            error = OutputValidationError("schema", f"Action validation failed: {e}", output)
            if self.strict:
                raise error
            logger.warning(error)
            return None

        # Security checks
        try:
            self._check_security(action.title)
            self._check_security(action.description)
        except OutputValidationError as error:
            if self.strict:
                raise
            logger.warning(error)
            return None

        # Domain validation
        try:
            valid_types = ["email_draft", "task", "purchase_order_draft", "price_change_draft"]
            assert action.type in valid_types, f"Invalid action type: {action.type}"
            assert len(action.title) > 5, "Title too short"
        except AssertionError as e:
            error = OutputValidationError("domain", str(e), output)
            if self.strict:
                raise error
            logger.warning(error)
            return None

        logger.info(f"Action validated: type={action.type}")
        return action

    def validate_executed_action(self, output: dict[str, Any]) -> ExecutedAction | None:
        """Validate Ejecutor output (ExecutedAction)."""
        try:
            executed = ExecutedAction(**output)
        except ValidationError as e:
            error = OutputValidationError("schema", f"ExecutedAction validation failed: {e}", output)
            if self.strict:
                raise error
            logger.warning(error)
            return None

        # Security check
        try:
            if isinstance(executed.result, str):
                self._check_security(executed.result)
        except OutputValidationError as error:
            if self.strict:
                raise
            logger.warning(error)
            return None

        # Domain validation
        try:
            valid_types = ["email_draft", "task", "purchase_order_draft", "price_change_draft", "nota_manual"]
            assert executed.type in valid_types, f"Invalid type: {executed.type}"
            assert len(executed.result) > 5, "Result too short"
        except AssertionError as e:
            error = OutputValidationError("domain", str(e), output)
            if self.strict:
                raise error
            logger.warning(error)
            return None

        logger.info(f"ExecutedAction validated: type={executed.type}")
        return executed

    def validate_decision(self, output: dict[str, Any]) -> Decision:
        """Validate human decision."""
        try:
            decision = Decision(**output)
        except ValidationError as e:
            raise OutputValidationError("schema", f"Decision validation failed: {e}", output)

        valid_kinds = ["approve", "edit", "reject", "request_changes"]
        if decision.kind not in valid_kinds:
            raise OutputValidationError("domain", f"Invalid kind: {decision.kind}", output)

        logger.info(f"Decision validated: kind={decision.kind}")
        return decision

    def validate_rejection_classifier(self, output: dict[str, Any]) -> RejectionClassifierOutput:
        """Validate rejection routing."""
        try:
            classifier = RejectionClassifierOutput(**output)
        except ValidationError as e:
            raise OutputValidationError("schema", f"Classifier validation failed: {e}", output)

        valid_destinos = ["causa", "propuesta", "ambos", "ninguno"]
        if classifier.destino not in valid_destinos:
            raise OutputValidationError("domain", f"Invalid destino: {classifier.destino}", output)

        logger.info(f"RejectionClassifier validated: destino={classifier.destino}")
        return classifier

    def _check_security(self, text: str) -> None:
        """Check for security issues."""
        # Check unfilled placeholders
        placeholders = re.findall(r'\{[^}]+\}', text)
        if placeholders:
            raise OutputValidationError("security", f"Unfilled placeholders: {placeholders}", text)

        # Check for SQL injection keywords
        if re.search(r"(UNION|DROP|DELETE|INSERT|UPDATE|SELECT)\s", text, re.IGNORECASE):
            raise OutputValidationError("security", "SQL injection pattern detected", text)

        # Check for prompt injection keywords
        if re.search(r"(ignore|override|bypass|system.*override)", text, re.IGNORECASE):
            raise OutputValidationError("security", "Prompt injection pattern detected", text)
