# -*- coding: utf-8 -*-
from .gst_dashboard_filters import normalize_filters, period_domain_keys
from .gst_dashboard_service import empty_section


def get_filing_stats(env, filters, availability):
    """Aggregate filing KPIs from armora.gst.filing stored counters."""
    if not availability.get('filing'):
        return empty_section(
            'filing',
            available=False,
            message='GST Filing analytics unavailable — install Armora GST Filing.',
        )

    filters = normalize_filters(filters)
    from .gst_dashboard_service import aggregate_model
    Filing = aggregate_model(env, 'armora.gst.filing')
    domain = period_domain_keys(filters) + [('state', '!=', 'cancelled')]
    if filters.get('company_id'):
        domain.append(('company_id', '=', filters['company_id']))
    elif env.companies:
        domain.append(('company_id', 'in', env.companies.ids))
    if filters.get('gst_registration_id'):
        domain.append(('gst_registration_id', '=', filters['gst_registration_id']))

    filings = Filing.search(domain)
    by_state = {s: 0 for s in (
        'draft', 'data_loaded', 'validated', 'generated', 'submitted', 'filed',
    )}
    for state, count in Filing._read_group(domain, ['state'], ['__count']):
        if state in by_state:
            by_state[state] = count

    pending = by_state['draft'] + by_state['data_loaded']
    filing_errors = sum(filings.mapped('validation_error_count'))

    # Tax / document totals from matching GSTR-1 filings when present.
    gstr1 = filings.filtered(lambda f: f.filing_type == 'gstr1')
    taxable = sum(gstr1.mapped('amount_taxable'))
    cgst = sum(gstr1.mapped('amount_cgst'))
    sgst = sum(gstr1.mapped('amount_sgst'))
    igst = sum(gstr1.mapped('amount_igst'))
    cess = sum(gstr1.mapped('amount_cess'))
    total_tax = sum(gstr1.mapped('amount_total_tax'))

    section = empty_section('filing', available=True)
    section['kpis'] = {
        'filing_count': len(filings),
        'pending_filings': pending,
        'validated_filings': by_state['validated'],
        'generated_filings': by_state['generated'],
        'submitted_filings': by_state['submitted'],
        'filed_filings': by_state['filed'],
        'filing_errors': filing_errors,
        'taxable_value': taxable,
        'cgst': cgst,
        'sgst': sgst,
        'igst': igst,
        'cess': cess,
        'total_tax': total_tax,
        'document_count': sum(gstr1.mapped('document_count')),
        'credit_note_count': sum(gstr1.mapped('count_credit_note')),
        'debit_note_count': sum(gstr1.mapped('count_debit_note')),
    }
    section['rows'] = [{
        'id': f.id,
        'name': f.display_name,
        'filing_type': f.filing_type,
        'gstin': f.gstin,
        'return_period': f.return_period,
        'state': f.state,
        'validation_status': f.validation_status,
        'validation_error_count': f.validation_error_count,
        'amount_taxable': f.amount_taxable,
        'amount_cgst': f.amount_cgst,
        'amount_sgst': f.amount_sgst,
        'amount_igst': f.amount_igst,
        'amount_total_tax': f.amount_total_tax,
    } for f in filings[:50]]
    return section
