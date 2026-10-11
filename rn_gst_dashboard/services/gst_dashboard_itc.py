# -*- coding: utf-8 -*-
from .gst_dashboard_service import empty_section


def get_itc_stats(env, filters, availability):
    """ITC KPIs only when rn_gst_itc exposes an authoritative model.

    Does not invent ITC from GSTR-2B or accounting.
    """
    if not availability.get('itc'):
        return empty_section(
            'itc',
            available=False,
            message='ITC analytics unavailable — install Armora GST ITC.',
        )
    # Future: read exposed aggregates from rn.gst.itc (or successor).
    # Keep zeros until that module defines fields.
    section = empty_section('itc', available=True)
    section['kpis'] = {
        'eligible_itc': 0.0,
        'reconciled_itc': 0.0,
        'unreconciled_itc': 0.0,
        'blocked_itc': 0.0,
        'pending_review': 0,
        'itc_variance': 0.0,
    }
    section['message'] = (
        'Armora GST ITC is installed but no aggregate fields are exposed yet.'
    )
    return section
