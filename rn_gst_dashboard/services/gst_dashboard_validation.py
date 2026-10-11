# -*- coding: utf-8 -*-
from .gst_dashboard_filters import move_period_domain, normalize_filters
from .gst_dashboard_service import empty_section


def get_validation_stats(env, filters, availability):
    """Aggregate invoice validation KPIs from move status / issues."""
    if not availability.get('invoice_validation'):
        return empty_section(
            'invoice_validation',
            available=False,
            message='Invoice validation analytics unavailable — install Armora GST Invoice Validator.',
        )

    filters = normalize_filters(filters)
    Move = env['account.move']
    domain = move_period_domain(filters)
    if 'country_code' in Move._fields:
        domain = domain + [('country_code', '=', 'IN')]
    if 'rn_gst_validation_status' not in Move._fields:
        return empty_section(
            'invoice_validation',
            available=False,
            message='Invoice validation fields unavailable on account.move.',
        )

    # Document universe for the period.
    total = Move.search_count(domain)
    by_status = {
        'ok': 0,
        'warning': 0,
        'error': 0,
        'pending': 0,
        'skipped': 0,
    }
    for status, count in Move._read_group(domain, ['rn_gst_validation_status'], ['__count']):
        status = status or 'pending'
        if status in by_status:
            by_status[status] = count

    validated = by_status['ok'] + by_status['warning'] + by_status['error']
    unvalidated = by_status['pending'] + by_status['skipped']

    from .gst_dashboard_service import aggregate_model
    Issue = aggregate_model(env, 'rn.gst.invoice.issue')
    issue_domain = [('company_id', '=', filters['company_id'])] if filters.get('company_id') else []
    if not filters.get('company_id') and env.companies:
        issue_domain.append(('company_id', 'in', env.companies.ids))
    if filters.get('date_from'):
        issue_domain.append(('move_id.invoice_date', '>=', filters['date_from']))
    if filters.get('date_to'):
        issue_domain.append(('move_id.invoice_date', '<=', filters['date_to']))

    validation_errors = Issue.search_count(issue_domain + [('severity', '=', 'error')])
    validation_warnings = Issue.search_count(issue_domain + [('severity', '=', 'warning')])

    # Blocking ≈ moves with error status (engine treats error as blocking when configured).
    blocking_errors = by_status['error']

    section = empty_section('invoice_validation', available=True)
    section['kpis'] = {
        'validated_documents': validated,
        'validation_errors': validation_errors,
        'validation_warnings': validation_warnings,
        'blocking_errors': blocking_errors,
        'unvalidated_documents': unvalidated if total else by_status['pending'],
        'total_checked': total,
        'valid_documents': by_status['ok'],
        'status_error': by_status['error'],
        'status_warning': by_status['warning'],
    }
    return section
