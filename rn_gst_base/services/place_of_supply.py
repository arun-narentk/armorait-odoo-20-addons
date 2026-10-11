# -*- coding: utf-8 -*-
"""Place-of-supply helpers based on GST TIN codes (not state names)."""

from __future__ import annotations

from ..constants.state_codes import TIN_FOREIGN_COUNTRY, TIN_OTHER_TERRITORY
from ..constants.transaction import (
    SUPPLY_EXPORT,
    SUPPLY_INTER,
    SUPPLY_INTRA,
    SUPPLY_OTHER,
)
from ..exceptions import GstValidationError
from .state_codes import is_special_territory_code, normalize_state_code


def classify_supply_by_state_codes(supplier_state_code, place_of_supply_code):
    """Classify supply nature from supplier TIN and place-of-supply TIN.

    Does not guess missing codes. Returns one of:
    intra / inter / export / other
    """
    supplier = normalize_state_code(supplier_state_code)
    pos = normalize_state_code(place_of_supply_code)
    if not supplier or not pos:
        raise GstValidationError(
            'Supplier state code and place of supply code are both required.'
        )
    if pos in (TIN_FOREIGN_COUNTRY, TIN_OTHER_TERRITORY) or is_special_territory_code(pos):
        return SUPPLY_EXPORT
    if supplier == pos:
        return SUPPLY_INTRA
    if is_special_territory_code(supplier):
        return SUPPLY_OTHER
    return SUPPLY_INTER


def is_intra_state_supply(supplier_state_code, place_of_supply_code):
    return classify_supply_by_state_codes(
        supplier_state_code, place_of_supply_code
    ) == SUPPLY_INTRA


def is_inter_state_supply(supplier_state_code, place_of_supply_code):
    return classify_supply_by_state_codes(
        supplier_state_code, place_of_supply_code
    ) == SUPPLY_INTER


def gstin_matches_place_of_supply(gstin_state_code, place_of_supply_code):
    """Return True when GSTIN prefix TIN matches POS TIN (both required)."""
    left = normalize_state_code(gstin_state_code)
    right = normalize_state_code(place_of_supply_code)
    if not left or not right:
        raise GstValidationError('GSTIN state code and place of supply are required.')
    return left == right
