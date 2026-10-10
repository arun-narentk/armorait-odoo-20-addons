# -*- coding: utf-8 -*-
"""GST validation severity constants (shared primitives only)."""

SEVERITY_ERROR = 'error'
SEVERITY_WARNING = 'warning'
SEVERITY_INFO = 'info'
SEVERITY_REVIEW = 'review'

SEVERITY_SELECTION = [
    (SEVERITY_ERROR, 'Error'),
    (SEVERITY_WARNING, 'Warning'),
    (SEVERITY_INFO, 'Info'),
    (SEVERITY_REVIEW, 'Review Required'),
]
