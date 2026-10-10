# -*- coding: utf-8 -*-
"""Shared exception classes for Armora GST base utilities.

These are pure Python exceptions for deterministic service-layer validation.
Odoo AbstractModel wrappers may convert them to ``ValidationError`` where
existing APIs already raise Odoo exceptions.
"""


class GstError(Exception):
    """Base exception for Armora GST foundation utilities."""


class GstFormatError(GstError):
    """Raised when a GST identifier or code has an invalid structure."""


class GstChecksumError(GstError):
    """Raised when a GSTIN fails checksum validation."""


class GstValidationError(GstError):
    """Raised for general GST validation failures (missing/inconsistent data)."""


class GstPeriodError(GstError):
    """Raised for invalid financial year or return period inputs."""


class GstMonetaryError(GstError):
    """Raised for invalid monetary / rounding inputs."""
