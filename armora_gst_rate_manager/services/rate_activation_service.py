# -*- coding: utf-8 -*-
"""Scheduled / controlled rate activation (idempotent).

Must not silently activate on conflict. Implemented in Prompt 18.
"""


def activate_scheduled_changes(env, company=None):
    del env, company
    return {
        'status': 'pending',
        'activated': 0,
        'failed': 0,
        'message': 'Scheduled GST rate activation is not implemented yet.',
    }
