# -*- coding: utf-8 -*-
"""Debit-note validation orchestration (additional liability).

Must not reuse credit-note maximum-credit / remaining-quantity logic.
"""


def validate_debit_note(env, move):
    """Return structured validation result. Implemented in Prompts 4–13."""
    del env
    return {
        'status': 'pending',
        'outcome': 'pending',
        'issues': [],
        'liability_direction': 'increase',
        'message': 'GST debit-note validation engine is not implemented yet.',
        'move': move,
    }
