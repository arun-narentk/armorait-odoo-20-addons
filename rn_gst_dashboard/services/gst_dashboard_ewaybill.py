# -*- coding: utf-8 -*-
from odoo import fields

from .gst_dashboard_filters import move_period_domain, normalize_filters
from .gst_dashboard_service import empty_section


def get_ewaybill_stats(env, filters, availability):
    """E-Way Bill counts from stored rn_ewb_status when present.

    Does not call GST portal APIs or generate E-Way Bills.
    """
    if not availability.get('ewaybill'):
        return empty_section(
            'ewaybill',
            available=False,
            message='E-Way Bill analytics unavailable — install Armora GST E-Way Bill modules.',
        )

    filters = normalize_filters(filters)
    Move = env['account.move']
    if 'rn_ewb_status' not in Move._fields:
        return empty_section(
            'ewaybill',
            available=False,
            message='E-Way Bill status field unavailable on account.move.',
        )

    domain = move_period_domain(filters) + [('rn_ewb_status', '!=', False)]
    by_status = {}
    total = 0
    for status, count in Move._read_group(domain, ['rn_ewb_status'], ['__count']):
        status = status or 'draft'
        by_status[status] = count
        total += count

    expired = 0
    if 'rn_ewb_validity_date' in Move._fields:
        now = fields.Datetime.now()
        expired = Move.search_count(domain + [
            ('rn_ewb_status', '=', 'active'),
            ('rn_ewb_validity_date', '<', now),
        ])

    section = empty_section('ewaybill', available=True)
    section['kpis'] = {
        'total': total,
        'generated': by_status.get('active', 0) + by_status.get('closed', 0) + by_status.get('cancelled', 0),
        'active': by_status.get('active', 0),
        'expired': expired,
        'cancelled': by_status.get('cancelled', 0),
        'pending': by_status.get('draft', 0),
    }
    return section
