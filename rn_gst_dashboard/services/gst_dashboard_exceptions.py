# -*- coding: utf-8 -*-
from .gst_dashboard_service import empty_section


def get_exception_stats(env, filters, availability):
    if not availability.get('exceptions'):
        return empty_section(
            'exceptions',
            available=False,
            message='Exception Center unavailable — install Armora GST Exception Center.',
        )
    # Scaffold has no domain model yet.
    section = empty_section('exceptions', available=True)
    section['kpis'] = {
        'open_exceptions': 0,
        'critical_exceptions': 0,
        'high_exceptions': 0,
        'resolved_exceptions': 0,
    }
    section['message'] = (
        'Exception Center is installed but no exception model is available yet.'
    )
    return section
