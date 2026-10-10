# -*- coding: utf-8 -*-
"""Configured GST rate lookup (no invoice tax calculation)."""


def get_rate(env, payload=None):
    """Return structured lookup result. Implemented in Prompt 13."""
    del env
    return {
        'status': 'not_implemented',
        'rate': False,
        'conflicts': [],
        'message': 'GST rate lookup service is not implemented yet.',
        'payload': payload or {},
    }
