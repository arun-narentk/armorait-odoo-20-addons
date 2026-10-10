# -*- coding: utf-8 -*-
from .gst_dashboard_filters import normalize_filters, period_domain_keys
from .gst_dashboard_service import empty_section


def get_2b_stats(env, filters, availability):
    """Aggregate GSTR-2B KPIs from stored reconciliation counters."""
    if not availability.get('reconciliation_2b'):
        return empty_section(
            'reconciliation_2b',
            available=False,
            message='GSTR-2B analytics unavailable — install Armora GST 2B Reconciliation.',
        )

    filters = normalize_filters(filters)
    from .gst_dashboard_service import aggregate_model
    Gstr2b = aggregate_model(env, 'armora.gst.gstr2b')
    domain = period_domain_keys(filters) + [('state', '!=', 'cancelled')]
    if filters.get('company_id'):
        domain.append(('company_id', '=', filters['company_id']))
    elif env.companies:
        domain.append(('company_id', 'in', env.companies.ids))
    recons = Gstr2b.search(domain)

    section = empty_section('reconciliation_2b', available=True)
    section['kpis'] = {
        'total_2b_records': sum(recons.mapped('line_count')),
        'exact_matches': sum(recons.mapped('count_matched')),
        # No dedicated partial-match state in 2B; keep 0 (disputed belongs in manual_review).
        'partial_matches': 0,
        'mismatches': sum(recons.mapped('count_mismatch')),
        'missing_in_books': sum(recons.mapped('count_missing_odoo')),
        'missing_in_2b': sum(recons.mapped('count_missing_2b')),
        'manual_review': sum(recons.mapped('count_disputed')) + sum(recons.mapped('count_ignored')),
        'amount_itc_total': sum(recons.mapped('amount_itc_total')),
        'amount_matched': sum(recons.mapped('amount_matched')),
        'amount_mismatch': sum(recons.mapped('amount_mismatch')),
        'amount_missing_odoo': sum(recons.mapped('amount_missing_odoo')),
        'amount_missing_2b': sum(recons.mapped('amount_missing_2b')),
    }
    section['rows'] = [{
        'id': r.id,
        'name': r.display_name,
        'gstin': r.gstin,
        'state': r.state,
        'line_count': r.line_count,
        'count_matched': r.count_matched,
        'count_mismatch': r.count_mismatch,
        'count_missing_odoo': r.count_missing_odoo,
        'count_missing_2b': r.count_missing_2b,
    } for r in recons[:50]]
    return section
