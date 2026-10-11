# -*- coding: utf-8 -*-
"""Orchestration service for HSN/SAC validation.

Coordinates format, consistency and optional provider checks.
Persists results via ORM models once Prompt 4–5 land.
"""


def validate(env, payload):
    """Run validation for the given payload. Implemented in Prompt 5."""
    del env  # reserved for ORM access
    return {
        'status': 'pending',
        'format_valid': None,
        'externally_verified': False,
        'issues': [],
        'payload': payload or {},
        'message': 'HSN/SAC validation engine is not implemented yet.',
    }
