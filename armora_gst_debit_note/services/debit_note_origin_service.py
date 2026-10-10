# -*- coding: utf-8 -*-
"""Original invoice linkage helpers for debit notes (debit_origin_id)."""


def get_origin(move):
    """Return the original move linked via debit_origin_id, or empty recordset."""
    return getattr(move, 'debit_origin_id', move.env['account.move'])


def validate_origin_link(env, move):
    """Structured origin checks. Implemented in Prompt 6."""
    del env
    origin = get_origin(move)
    return {
        'status': 'pending',
        'has_origin': bool(origin),
        'origin': origin,
        'issues': [],
        'message': 'Debit-note original invoice validation is not implemented yet.',
    }
