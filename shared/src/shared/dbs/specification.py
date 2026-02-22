"""Specification pattern for composable business rules.

Specifications are *predicates* that can be combined with boolean
operators (``&``, ``|``, ``~``) to form complex, reusable, and
testable business rules.

They complement the existing :class:`~shared.dbs.Filter` system:
while ``Filter`` maps directly to database-level WHERE clauses,
specifications operate at the **domain level** and can be evaluated
against any Python object.

Quick start::

    from shared.dbs.specification import Specification, Attr

    # Simple attribute spec
    active = Attr("is_active", True)
    premium = Attr("plan", "premium")
    high_value = Attr("lifetime_value", 1000, op="gte")

    # Compose
    target_users = active & premium & high_value

    # Evaluate in-memory
    assert target_users.is_satisfied_by(user)

    # Convert to repository Filters
    filters = target_users.to_filters()
    results = await repo.find(filters=filters)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from shared.dbs.repository import Filter, FilterOperator

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Evaluator dispatch table (replaces complex if-chain in AttributeSpec)
# ---------------------------------------------------------------------------

_EVALUATORS: dict[FilterOperator, Callable[[Any, Any], bool]] = {
    FilterOperator.EQ: lambda attr, val: attr == val,
    FilterOperator.NE: lambda attr, val: attr != val,
    FilterOperator.GT: lambda attr, val: attr is not None and attr > val,
    FilterOperator.GE: lambda attr, val: attr is not None and attr >= val,
    FilterOperator.GTE: lambda attr, val: attr is not None and attr >= val,
    FilterOperator.LT: lambda attr, val: attr is not None and attr < val,
    FilterOperator.LE: lambda attr, val: attr is not None and attr <= val,
    FilterOperator.LTE: lambda attr, val: attr is not None and attr <= val,
    FilterOperator.LIKE: lambda attr, val: (
        val.lower() in str(attr).lower() if attr is not None else False
    ),
    FilterOperator.CONTAINS: lambda attr, val: val in attr if attr is not None else False,
    FilterOperator.STARTS_WITH: lambda attr, val: (
        str(attr).startswith(str(val)) if attr is not None else False
    ),
    FilterOperator.ENDS_WITH: lambda attr, val: (
        str(attr).endswith(str(val)) if attr is not None else False
    ),
    FilterOperator.IN: lambda attr, val: attr in val,
    FilterOperator.NOT_IN: lambda attr, val: attr not in val,
    FilterOperator.IS_NULL: lambda attr, _val: attr is None,
    FilterOperator.IS_NOT_NULL: lambda attr, _val: attr is not None,
}

# Mapping from short operator names to FilterOperator values
_OP_MAP: dict[str, FilterOperator] = {
    "eq": FilterOperator.EQ,
    "ne": FilterOperator.NE,
    "gt": FilterOperator.GT,
    "ge": FilterOperator.GE,
    "gte": FilterOperator.GTE,
    "lt": FilterOperator.LT,
    "le": FilterOperator.LE,
    "lte": FilterOperator.LTE,
    "like": FilterOperator.LIKE,
    "contains": FilterOperator.CONTAINS,
    "starts_with": FilterOperator.STARTS_WITH,
    "ends_with": FilterOperator.ENDS_WITH,
    "in": FilterOperator.IN,
    "not_in": FilterOperator.NOT_IN,
    "is_null": FilterOperator.IS_NULL,
    "is_not_null": FilterOperator.IS_NOT_NULL,
}


# ======================================================================
# Base Specification
# ======================================================================


class Specification(ABC, Generic[T]):
    """Abstract base for all specifications.

    A specification encapsulates a single business rule that can
    be evaluated against a candidate object and optionally converted
    to a list of :class:`Filter` instances for repository queries.

    Supports boolean algebra via ``&`` (and), ``|`` (or), ``~`` (not).

    Example::

        class IsActive(Specification[User]):
            def is_satisfied_by(self, candidate: User) -> bool:
                return candidate.is_active

        class HasRole(Specification[User]):
            def __init__(self, role: str) -> None:
                self._role = role
            def is_satisfied_by(self, candidate: User) -> bool:
                return self._role in candidate.roles

        spec = IsActive() & HasRole("admin")
        assert spec.is_satisfied_by(active_admin)
    """

    @abstractmethod
    def is_satisfied_by(self, candidate: T) -> bool:
        """Evaluate the specification against *candidate*.

        Args:
            candidate: The object to test.

        Returns:
            ``True`` if the candidate satisfies this specification.
        """
        ...

    def can_convert_to_filters(self) -> bool:
        """Return ``True`` if this specification can produce filters.

        Override in subclasses that cannot be converted (e.g. OR, NOT).
        """
        return True

    def to_filters(self) -> list[Filter]:
        """Convert the specification to repository :class:`Filter` objects.

        Not all specifications can be converted — :class:`OrSpecification`
        and :class:`NotSpecification` raise :class:`NotImplementedError`.
        Use :meth:`can_convert_to_filters` to check first.

        Returns:
            A list of :class:`Filter` instances (possibly empty).

        Raises:
            NotImplementedError: If the spec cannot be expressed as filters.
        """
        return []

    # ------------------------------------------------------------------
    # Boolean operators
    # ------------------------------------------------------------------

    def __and__(self, other: Specification[T]) -> AndSpecification[T]:
        return AndSpecification(self, other)

    def __or__(self, other: Specification[T]) -> OrSpecification[T]:
        return OrSpecification(self, other)

    def __invert__(self) -> NotSpecification[T]:
        return NotSpecification(self)

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def __call__(self, candidate: T) -> bool:
        """Allow ``spec(obj)`` as shorthand for ``spec.is_satisfied_by(obj)``."""
        return self.is_satisfied_by(candidate)


# ======================================================================
# Combinators
# ======================================================================


class AndSpecification(Specification[T]):
    """Logical AND of two specifications.

    Satisfied when **both** operands are satisfied.  ``to_filters``
    returns the concatenation of both operands' filters (AND semantics
    in a WHERE clause).
    """

    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        self._left = left
        self._right = right

    @property
    def left(self) -> Specification[T]:
        return self._left

    @property
    def right(self) -> Specification[T]:
        return self._right

    def is_satisfied_by(self, candidate: T) -> bool:
        return self._left.is_satisfied_by(candidate) and self._right.is_satisfied_by(candidate)

    def to_filters(self) -> list[Filter]:
        return self._left.to_filters() + self._right.to_filters()


class OrSpecification(Specification[T]):
    """Logical OR of two specifications.

    Satisfied when **either** operand is satisfied.

    .. warning::
        ``to_filters()`` raises :class:`NotImplementedError` because
        most repository layers do not support OR-combined filters
        natively.  Use :meth:`can_convert_to_filters` to check first,
        or perform in-memory evaluation.
    """

    def __init__(self, left: Specification[T], right: Specification[T]) -> None:
        self._left = left
        self._right = right

    @property
    def left(self) -> Specification[T]:
        return self._left

    @property
    def right(self) -> Specification[T]:
        return self._right

    def is_satisfied_by(self, candidate: T) -> bool:
        return self._left.is_satisfied_by(candidate) or self._right.is_satisfied_by(candidate)

    def can_convert_to_filters(self) -> bool:
        return False

    def to_filters(self) -> list[Filter]:
        raise NotImplementedError(
            "OR specifications cannot be converted to repository filters. "
            "Use in-memory evaluation via is_satisfied_by() or restructure "
            "as AND-compatible filters."
        )


class NotSpecification(Specification[T]):
    """Logical NOT of a specification.

    Satisfied when the wrapped specification is **not** satisfied.

    .. warning::
        ``to_filters()`` raises :class:`NotImplementedError` because
        generic negation is not representable by the :class:`Filter`
        model.
    """

    def __init__(self, spec: Specification[T]) -> None:
        self._spec = spec

    @property
    def inner(self) -> Specification[T]:
        return self._spec

    def is_satisfied_by(self, candidate: T) -> bool:
        return not self._spec.is_satisfied_by(candidate)

    def can_convert_to_filters(self) -> bool:
        return False

    def to_filters(self) -> list[Filter]:
        raise NotImplementedError(
            "NOT specifications cannot be converted to repository filters. "
            "Use in-memory evaluation via is_satisfied_by()."
        )


# ======================================================================
# Concrete specifications
# ======================================================================


@dataclass(frozen=True)
class AttributeSpec(Specification[Any]):
    """Specification that tests a single attribute with an operator.

    This is the workhorse specification — it can compare any attribute
    with a value using the operators defined in :class:`FilterOperator`,
    and it converts cleanly to a :class:`Filter`.

    Args:
        field: Attribute name on the candidate object.
        value: Expected value (ignored for IS_NULL / IS_NOT_NULL).
        operator: Comparison operator (default ``eq``).  Accepts a
            :class:`FilterOperator` or a string shorthand like
            ``"eq"``, ``"gte"``, ``"in"``, etc.

    Example::

        spec = AttributeSpec("age", 18, "gte")
        assert spec.is_satisfied_by(user_with_age_21)
        [f] = spec.to_filters()
        assert f.operator == FilterOperator.GTE
    """

    field: str
    value: Any = None
    operator: FilterOperator | str = FilterOperator.EQ

    def _resolved_op(self) -> FilterOperator:
        """Resolve string operator to FilterOperator.

        Raises:
            ValueError: If *operator* is a string that is not recognised.
        """
        if isinstance(self.operator, FilterOperator):
            return self.operator
        try:
            return _OP_MAP[self.operator]
        except KeyError:
            raise ValueError(
                f"Unknown operator '{self.operator}'. "
                f"Valid operators: {', '.join(sorted(_OP_MAP))}"
            ) from None

    # ------------------------------------------------------------------
    # Core evaluation
    # ------------------------------------------------------------------

    def is_satisfied_by(self, candidate: Any) -> bool:
        attr = getattr(candidate, self.field, None)
        op = self._resolved_op()
        evaluator = _EVALUATORS.get(op)
        if evaluator is None:  # pragma: no cover
            return False
        return evaluator(attr, self.value)

    # ------------------------------------------------------------------
    # Filter conversion
    # ------------------------------------------------------------------

    def to_filters(self) -> list[Filter]:
        return [Filter(field=self.field, value=self.value, operator=self._resolved_op())]


# ======================================================================
# Shorthand factory
# ======================================================================


def Attr(
    field: str,
    value: Any = None,
    op: FilterOperator | str = FilterOperator.EQ,
) -> AttributeSpec:
    """Convenience factory for :class:`AttributeSpec`.

    Args:
        field: Attribute name.
        value: Expected value.
        op: Operator (string or :class:`FilterOperator`).

    Returns:
        An :class:`AttributeSpec` instance.

    Example::

        spec = Attr("status", "active") & Attr("age", 18, "gte")
    """
    return AttributeSpec(field=field, value=value, operator=op)


class AlwaysTrue(Specification[Any]):
    """Specification that is always satisfied (identity for AND)."""

    def is_satisfied_by(self, candidate: Any) -> bool:
        return True

    def to_filters(self) -> list[Filter]:
        """Always-true requires no filters (no WHERE constraint)."""
        return []


class AlwaysFalse(Specification[Any]):
    """Specification that is never satisfied (identity for OR)."""

    def is_satisfied_by(self, candidate: Any) -> bool:
        return False

    def to_filters(self) -> list[Filter]:
        """Always-false cannot be expressed as filters."""
        return []
