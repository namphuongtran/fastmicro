"""Tests for the Specification pattern."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from shared.dbs import (
    Filter,
    FilterOperator,
)
from shared.dbs.specification import (
    AlwaysFalse,
    AlwaysTrue,
    AndSpecification,
    Attr,
    AttributeSpec,
    NotSpecification,
    OrSpecification,
    Specification,
)

# ======================================================================
# Fixtures — sample domain objects
# ======================================================================


@dataclass
class Product:
    id: str
    name: str
    price: float
    category: str
    is_active: bool
    tags: list[str] | None = None


WIDGET = Product("p1", "Widget", 9.99, "tools", True, ["sale"])
GADGET = Product("p2", "Gadget", 49.99, "electronics", True, ["new"])
GIZMO = Product("p3", "Gizmo", 199.99, "electronics", False, None)
CHEAP = Product("p4", "Cheap Thing", 1.00, "misc", True, ["sale", "clearance"])
EXPENSIVE = Product("p5", "Expensive", 200.00, "luxury", True, ["premium"])


# ======================================================================
# Custom specification for testing
# ======================================================================


class IsActive(Specification["Product"]):
    def is_satisfied_by(self, candidate: Product) -> bool:
        return candidate.is_active


class HasTag(Specification["Product"]):
    def __init__(self, tag: str) -> None:
        self._tag = tag

    def is_satisfied_by(self, candidate: Product) -> bool:
        return candidate.tags is not None and self._tag in candidate.tags


# ======================================================================
# TestAttributeSpec — EQ
# ======================================================================


class TestAttributeSpecEq:
    def test_eq_match(self) -> None:
        spec = AttributeSpec("category", "electronics")
        assert spec.is_satisfied_by(GADGET)

    def test_eq_no_match(self) -> None:
        spec = AttributeSpec("category", "electronics")
        assert not spec.is_satisfied_by(WIDGET)

    def test_eq_string_op(self) -> None:
        spec = AttributeSpec("category", "electronics", "eq")
        assert spec.is_satisfied_by(GADGET)

    def test_ne(self) -> None:
        spec = AttributeSpec("category", "tools", FilterOperator.NE)
        assert spec.is_satisfied_by(GADGET)
        assert not spec.is_satisfied_by(WIDGET)


# ======================================================================
# TestAttributeSpec — comparison operators
# ======================================================================


class TestAttributeSpecComparison:
    def test_gt(self) -> None:
        spec = AttributeSpec("price", 10.0, FilterOperator.GT)
        assert spec.is_satisfied_by(GADGET)
        assert not spec.is_satisfied_by(WIDGET)

    def test_gte_string(self) -> None:
        spec = AttributeSpec("price", 9.99, "gte")
        assert spec.is_satisfied_by(WIDGET)  # exactly 9.99
        assert not spec.is_satisfied_by(CHEAP)  # 1.00

    def test_ge_enum(self) -> None:
        spec = AttributeSpec("price", 49.99, FilterOperator.GE)
        assert spec.is_satisfied_by(GADGET)
        assert spec.is_satisfied_by(GIZMO)
        assert not spec.is_satisfied_by(WIDGET)

    def test_lt(self) -> None:
        spec = AttributeSpec("price", 50.0, FilterOperator.LT)
        assert spec.is_satisfied_by(WIDGET)
        assert not spec.is_satisfied_by(GIZMO)

    def test_le(self) -> None:
        spec = AttributeSpec("price", 9.99, FilterOperator.LE)
        assert spec.is_satisfied_by(WIDGET)
        assert spec.is_satisfied_by(CHEAP)
        assert not spec.is_satisfied_by(GADGET)

    def test_lte_string(self) -> None:
        spec = AttributeSpec("price", 1.00, "lte")
        assert spec.is_satisfied_by(CHEAP)
        assert not spec.is_satisfied_by(WIDGET)

    def test_none_attribute_comparison(self) -> None:
        """Comparison with None attribute returns False."""
        spec = AttributeSpec("nonexistent", 10, FilterOperator.GT)
        assert not spec.is_satisfied_by(WIDGET)


# ======================================================================
# TestAttributeSpec — string operators
# ======================================================================


class TestAttributeSpecString:
    def test_like(self) -> None:
        spec = AttributeSpec("name", "wid", FilterOperator.LIKE)
        assert spec.is_satisfied_by(WIDGET)
        assert not spec.is_satisfied_by(GADGET)

    def test_like_case_insensitive(self) -> None:
        spec = AttributeSpec("name", "WID", FilterOperator.LIKE)
        assert spec.is_satisfied_by(WIDGET)

    def test_contains(self) -> None:
        spec = AttributeSpec("name", "adge", FilterOperator.CONTAINS)
        assert spec.is_satisfied_by(GADGET)

    def test_starts_with(self) -> None:
        spec = AttributeSpec("name", "Giz", FilterOperator.STARTS_WITH)
        assert spec.is_satisfied_by(GIZMO)
        assert not spec.is_satisfied_by(WIDGET)

    def test_ends_with(self) -> None:
        spec = AttributeSpec("name", "get", FilterOperator.ENDS_WITH)
        assert spec.is_satisfied_by(GADGET)
        assert not spec.is_satisfied_by(GIZMO)

    def test_like_none_attribute(self) -> None:
        spec = AttributeSpec("nonexistent", "x", FilterOperator.LIKE)
        assert not spec.is_satisfied_by(WIDGET)

    def test_contains_none(self) -> None:
        spec = AttributeSpec("nonexistent", "x", FilterOperator.CONTAINS)
        assert not spec.is_satisfied_by(WIDGET)

    def test_starts_with_none(self) -> None:
        spec = AttributeSpec("nonexistent", "x", FilterOperator.STARTS_WITH)
        assert not spec.is_satisfied_by(WIDGET)

    def test_ends_with_none(self) -> None:
        spec = AttributeSpec("nonexistent", "x", FilterOperator.ENDS_WITH)
        assert not spec.is_satisfied_by(WIDGET)


# ======================================================================
# TestAttributeSpec — collection operators
# ======================================================================


class TestAttributeSpecCollection:
    def test_in(self) -> None:
        spec = AttributeSpec("category", ["tools", "electronics"], FilterOperator.IN)
        assert spec.is_satisfied_by(WIDGET)
        assert spec.is_satisfied_by(GADGET)
        assert not spec.is_satisfied_by(CHEAP)

    def test_not_in(self) -> None:
        spec = AttributeSpec("category", ["tools", "misc"], FilterOperator.NOT_IN)
        assert spec.is_satisfied_by(GADGET)
        assert not spec.is_satisfied_by(WIDGET)


# ======================================================================
# TestAttributeSpec — null operators
# ======================================================================


class TestAttributeSpecNull:
    def test_is_null(self) -> None:
        spec = AttributeSpec("tags", None, FilterOperator.IS_NULL)
        assert spec.is_satisfied_by(GIZMO)
        assert not spec.is_satisfied_by(WIDGET)

    def test_is_not_null(self) -> None:
        spec = AttributeSpec("tags", None, FilterOperator.IS_NOT_NULL)
        assert spec.is_satisfied_by(WIDGET)
        assert not spec.is_satisfied_by(GIZMO)


# ======================================================================
# TestAttributeSpec — to_filters
# ======================================================================


class TestAttributeSpecToFilters:
    def test_to_filters_basic(self) -> None:
        spec = AttributeSpec("name", "Widget")
        filters = spec.to_filters()
        assert len(filters) == 1
        assert filters[0].field == "name"
        assert filters[0].value == "Widget"
        assert filters[0].operator == FilterOperator.EQ

    def test_to_filters_with_string_op(self) -> None:
        spec = AttributeSpec("price", 10, "gte")
        [f] = spec.to_filters()
        assert f.operator == FilterOperator.GTE

    def test_to_filters_with_enum_op(self) -> None:
        spec = AttributeSpec("category", ["a", "b"], FilterOperator.IN)
        [f] = spec.to_filters()
        assert f.operator == FilterOperator.IN


# ======================================================================
# TestAttr shorthand
# ======================================================================


class TestAttr:
    def test_attr_default_eq(self) -> None:
        spec = Attr("name", "Widget")
        assert spec.is_satisfied_by(WIDGET)

    def test_attr_with_string_op(self) -> None:
        spec = Attr("price", 10, op="gt")
        assert spec.is_satisfied_by(GADGET)

    def test_attr_with_enum_op(self) -> None:
        spec = Attr("is_active", True, op=FilterOperator.EQ)
        assert spec.is_satisfied_by(WIDGET)


# ======================================================================
# TestAndSpecification
# ======================================================================


class TestAndSpec:
    def test_both_true(self) -> None:
        spec = IsActive() & HasTag("sale")
        assert spec.is_satisfied_by(WIDGET)

    def test_left_false(self) -> None:
        spec = IsActive() & HasTag("sale")
        assert not spec.is_satisfied_by(GIZMO)

    def test_right_false(self) -> None:
        spec = IsActive() & HasTag("new")
        assert not spec.is_satisfied_by(WIDGET)

    def test_to_filters_combines(self) -> None:
        a = Attr("is_active", True)
        b = Attr("category", "electronics")
        combined = a & b
        filters = combined.to_filters()
        assert len(filters) == 2
        assert filters[0].field == "is_active"
        assert filters[1].field == "category"

    def test_properties(self) -> None:
        left = IsActive()
        right = HasTag("sale")
        spec = AndSpecification(left, right)
        assert spec.left is left
        assert spec.right is right


# ======================================================================
# TestOrSpecification
# ======================================================================


class TestOrSpec:
    def test_either_true(self) -> None:
        spec = IsActive() | HasTag("new")
        assert spec.is_satisfied_by(WIDGET)  # active but no "new"
        assert spec.is_satisfied_by(GADGET)  # active and "new"

    def test_both_false(self) -> None:
        spec = Attr("category", "food") | Attr("price", 0.0)
        assert not spec.is_satisfied_by(WIDGET)

    def test_to_filters_raises(self) -> None:
        """OR specs cannot be converted to filters."""
        spec = Attr("a", 1) | Attr("b", 2)
        assert not spec.can_convert_to_filters()
        with pytest.raises(NotImplementedError):
            spec.to_filters()

    def test_properties(self) -> None:
        left = IsActive()
        right = HasTag("x")
        spec = OrSpecification(left, right)
        assert spec.left is left
        assert spec.right is right


# ======================================================================
# TestNotSpecification
# ======================================================================


class TestNotSpec:
    def test_inverts_true(self) -> None:
        spec = ~IsActive()
        assert spec.is_satisfied_by(GIZMO)

    def test_inverts_false(self) -> None:
        spec = ~IsActive()
        assert not spec.is_satisfied_by(WIDGET)

    def test_to_filters_raises(self) -> None:
        spec = ~Attr("is_active", True)
        assert not spec.can_convert_to_filters()
        with pytest.raises(NotImplementedError):
            spec.to_filters()

    def test_inner(self) -> None:
        inner = IsActive()
        spec = NotSpecification(inner)
        assert spec.inner is inner


# ======================================================================
# TestAlwaysTrue / TestAlwaysFalse
# ======================================================================


class TestIdentitySpecs:
    def test_always_true(self) -> None:
        spec = AlwaysTrue()
        assert spec.is_satisfied_by(WIDGET)
        assert spec.is_satisfied_by(GIZMO)

    def test_always_false(self) -> None:
        spec = AlwaysFalse()
        assert not spec.is_satisfied_by(WIDGET)
        assert not spec.is_satisfied_by(GIZMO)


# ======================================================================
# Test complex composition
# ======================================================================


class TestComplexComposition:
    def test_and_or_chain(self) -> None:
        """(active AND electronics) OR (tag=sale)."""
        spec = (IsActive() & Attr("category", "electronics")) | HasTag("sale")
        assert spec.is_satisfied_by(GADGET)  # active electronics
        assert spec.is_satisfied_by(WIDGET)  # has sale tag
        assert not spec.is_satisfied_by(GIZMO)  # inactive, no sale tag

    def test_double_negation(self) -> None:
        spec = ~~IsActive()
        assert spec.is_satisfied_by(WIDGET)
        assert not spec.is_satisfied_by(GIZMO)

    def test_not_and(self) -> None:
        """NOT (active AND expensive >= 100)."""
        spec = ~(IsActive() & Attr("price", 100, "gte"))
        assert spec.is_satisfied_by(WIDGET)  # active but price 9.99 < 100
        assert spec.is_satisfied_by(GIZMO)  # inactive
        assert not spec.is_satisfied_by(EXPENSIVE)  # active AND price 200 >= 100

    def test_callable_shorthand(self) -> None:
        spec = IsActive()
        assert spec(WIDGET) is True
        assert spec(GIZMO) is False

    def test_chained_and_to_filters(self) -> None:
        """Three-way AND produces three filters."""
        spec = Attr("a", 1) & Attr("b", 2) & Attr("c", 3)
        filters = spec.to_filters()
        fields = [f.field for f in filters]
        assert fields == ["a", "b", "c"]


# ======================================================================
# Test unknown operator raises ValueError
# ======================================================================


class TestUnknownOperator:
    def test_unknown_string_operator_raises(self) -> None:
        """Unknown operator strings must raise ValueError, not silently default to EQ."""
        spec = AttributeSpec("price", 10, "bad_operator")
        with pytest.raises(ValueError, match="Unknown operator"):
            spec.is_satisfied_by(WIDGET)

    def test_unknown_string_operator_to_filters_raises(self) -> None:
        spec = AttributeSpec("price", 10, "not_a_real_op")
        with pytest.raises(ValueError, match="Unknown operator"):
            spec.to_filters()


# ======================================================================
# Test can_convert_to_filters
# ======================================================================


class TestCanConvertToFilters:
    def test_attribute_spec_can_convert(self) -> None:
        assert Attr("x", 1).can_convert_to_filters()

    def test_and_spec_can_convert(self) -> None:
        assert (Attr("x", 1) & Attr("y", 2)).can_convert_to_filters()

    def test_or_spec_cannot_convert(self) -> None:
        assert not (Attr("x", 1) | Attr("y", 2)).can_convert_to_filters()

    def test_not_spec_cannot_convert(self) -> None:
        assert not (~Attr("x", 1)).can_convert_to_filters()

    def test_always_true_can_convert(self) -> None:
        assert AlwaysTrue().can_convert_to_filters()

    def test_always_false_can_convert(self) -> None:
        assert AlwaysFalse().can_convert_to_filters()
