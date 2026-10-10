# -*- coding: utf-8 -*-
from .gst_dashboard_filters import move_period_domain, normalize_filters
from .gst_dashboard_service import empty_section


def get_einvoice_stats(env, filters, availability):
    """E-Invoice counts from account.move.l10n_in_edi_status when available.

    Does not call GST portal APIs or generate IRNs.
    """
    if not availability.get('einvoice'):
        return empty_section(
            'einvoice',
            available=False,
            message='E-Invoice analytics unavailable — install Armora GST E-Invoice modules.',
        )

    filters = normalize_filters(filters)
    Move = env['account.move']
    if 'l10n_in_edi_status' not in Move._fields:
        return empty_section(
            'einvoice',
            available=False,
            message='E-Invoice status field unavailable on account.move.',
        )

    # Cancelled e-invoices sit on cancelled moves, so do not keep only posted ones.
    domain = [leaf for leaf in move_period_domain(filters) if leaf[0] != 'state']
    domain += [('l10n_in_edi_status', '!=', False)]
    by_state = {}
    total = 0
    for state, count in Move._read_group(domain, ['l10n_in_edi_status'], ['__count']):
        by_state[state] = count
        total += count

    # A failed send keeps the 'to_send' status and stores the portal error on the move.
    failed = Move.search_count(domain + [
        ('l10n_in_edi_status', '=', 'to_send'),
        ('l10n_in_edi_error', '!=', False),
    ])
    generated = by_state.get('sent', 0)
    pending = by_state.get('to_send', 0) - failed
    cancelled = by_state.get('cancelled', 0)

    section = empty_section('einvoice', available=True)
    section['kpis'] = {
        'total': total,
        'generated': generated,
        'cancelled': cancelled,
        'failed': failed,
        'pending': pending,
    }
    return section
