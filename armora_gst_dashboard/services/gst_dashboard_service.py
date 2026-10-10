# -*- coding: utf-8 -*-
"""Dashboard aggregation facade.

Providers return empty/disabled results when optional modules are not installed.
"""
from .gst_dashboard_filters import move_period_domain, normalize_filters

# Technical module names used for soft detection.
MODULE_TECHNICAL_NAMES = {
    'filing': 'armora_gst_filing',
    'reconciliation_2b': 'armora_gst_2b_reconciliation',
    'invoice_validation': 'armora_gst_invoice_validator',
    'itc': 'armora_gst_itc',
    'einvoice': 'armora_gst_einvoice',
    'einvoice_monitor': 'armora_gst_einvoice_monitor',
    'ewaybill': 'armora_gst_ewaybill',
    'ewaybill_manager': 'armora_gst_ewaybill_manager',
    'exceptions': 'armora_gst_exception',
    'gstr3b': 'armora_gst_3b',
    'multi_gstin': 'armora_gst_multi_gstin',
    'audit': 'armora_gst_audit',
    'calendar': 'armora_gst_calendar',
}


def _module_installed(env, technical_name):
    Module = env['ir.module.module'].sudo()
    return bool(Module.search_count([
        ('name', '=', technical_name),
        ('state', '=', 'installed'),
    ]))


def _model_available(env, model_name):
    return model_name in env


def empty_section(key, available=False, message=None):
    return {
        'key': key,
        'available': available,
        'message': message or (
            None if available else 'Module not installed or data model unavailable.'
        ),
        'kpis': {},
        'rows': [],
        'actions': [],
    }


def aggregate_model(env, model_name):
    """Return a sudo browse for soft cross-module KPI aggregation.

    Dashboard users may not hold ACLs on every specialist module. Aggregation is
    still scoped to companies the user can access via ``env.companies``.
    """
    return env[model_name].sudo().with_context(allowed_company_ids=env.companies.ids)



def module_availability(env):
    """Return which dashboard sections can be populated."""
    filing = (
        _module_installed(env, MODULE_TECHNICAL_NAMES['filing'])
        and _model_available(env, 'armora.gst.filing')
    )
    recon_2b = (
        _module_installed(env, MODULE_TECHNICAL_NAMES['reconciliation_2b'])
        and _model_available(env, 'armora.gst.gstr2b')
    )
    validation = (
        _module_installed(env, MODULE_TECHNICAL_NAMES['invoice_validation'])
        and _model_available(env, 'armora.gst.invoice.issue')
    )
    itc = (
        _module_installed(env, MODULE_TECHNICAL_NAMES['itc'])
        and _model_available(env, 'armora.gst.itc')
    )
    einvoice = (
        _module_installed(env, MODULE_TECHNICAL_NAMES['einvoice'])
        or _module_installed(env, MODULE_TECHNICAL_NAMES['einvoice_monitor'])
    )
    ewaybill = (
        _module_installed(env, MODULE_TECHNICAL_NAMES['ewaybill'])
        or _module_installed(env, MODULE_TECHNICAL_NAMES['ewaybill_manager'])
    )
    exceptions = (
        _module_installed(env, MODULE_TECHNICAL_NAMES['exceptions'])
        and _model_available(env, 'armora.gst.exception')
    )
    return {
        'filing': filing,
        'reconciliation_2b': recon_2b,
        'invoice_validation': validation,
        'itc': itc,
        'einvoice': einvoice,
        'ewaybill': ewaybill,
        'exceptions': exceptions,
        'gstr3b': _module_installed(env, MODULE_TECHNICAL_NAMES['gstr3b']),
        'multi_gstin': _module_installed(env, MODULE_TECHNICAL_NAMES['multi_gstin']),
        'audit': _module_installed(env, MODULE_TECHNICAL_NAMES['audit']),
        'calendar': _module_installed(env, MODULE_TECHNICAL_NAMES['calendar']),
    }


def _overview_from_moves(env, filters):
    """Document counts and untaxed/tax totals from account.move (not GST split)."""
    filters = normalize_filters(filters)
    Move = env['account.move']
    domain = move_period_domain(filters)
    if 'country_code' in Move._fields:
        domain = domain + [('country_code', '=', 'IN')]

    kpis = {
        'total_invoices': 0,
        'total_vendor_bills': 0,
        'total_credit_notes': 0,
        'total_debit_notes': 0,
        'taxable_value': 0.0,
        'total_tax': 0.0,
    }
    for move_type, count, untaxed, tax in Move._read_group(
        domain, ['move_type'], ['__count', 'amount_untaxed:sum', 'amount_tax:sum'],
    ):
        untaxed = untaxed or 0.0
        tax = tax or 0.0
        if move_type == 'out_invoice':
            kpis['total_invoices'] += count
            kpis['taxable_value'] += untaxed
            kpis['total_tax'] += tax
        elif move_type == 'in_invoice':
            kpis['total_vendor_bills'] += count
            kpis['taxable_value'] += untaxed
            kpis['total_tax'] += tax
        elif move_type in ('out_refund', 'in_refund'):
            kpis['total_credit_notes'] += count
            # Credits reduce period taxable / tax totals (unsigned read_group sums).
            kpis['taxable_value'] -= untaxed
            kpis['total_tax'] -= tax
    # Debit notes: only when account_debit_note marks them; keep 0 without that module field.
    if 'debit_origin_id' in Move._fields:
        kpis['total_debit_notes'] = Move.search_count(domain + [('debit_origin_id', '!=', False)])
    return kpis


def get_dashboard_data(env, filters=None):
    """Single facade for dashboard payloads."""
    from . import gst_dashboard_2b
    from . import gst_dashboard_einvoice
    from . import gst_dashboard_ewaybill
    from . import gst_dashboard_exceptions
    from . import gst_dashboard_filings
    from . import gst_dashboard_itc
    from . import gst_dashboard_validation

    filters = normalize_filters(filters)
    availability = module_availability(env)

    filing = gst_dashboard_filings.get_filing_stats(env, filters, availability)
    recon = gst_dashboard_2b.get_2b_stats(env, filters, availability)
    validation = gst_dashboard_validation.get_validation_stats(env, filters, availability)
    itc = gst_dashboard_itc.get_itc_stats(env, filters, availability)
    einvoice = gst_dashboard_einvoice.get_einvoice_stats(env, filters, availability)
    ewaybill = gst_dashboard_ewaybill.get_ewaybill_stats(env, filters, availability)
    exceptions = gst_dashboard_exceptions.get_exception_stats(env, filters, availability)

    overview_kpis = _overview_from_moves(env, filters)
    # Prefer filing GSTR-1 tax split when available; keep move-based document counts.
    if filing.get('available') and filing.get('kpis'):
        fk = filing['kpis']
        if fk.get('taxable_value') or fk.get('total_tax') or fk.get('cgst') or fk.get('igst'):
            overview_kpis['taxable_value'] = fk.get('taxable_value') or 0.0
            overview_kpis['cgst'] = fk.get('cgst') or 0.0
            overview_kpis['sgst'] = fk.get('sgst') or 0.0
            overview_kpis['igst'] = fk.get('igst') or 0.0
            overview_kpis['cess'] = fk.get('cess') or 0.0
            overview_kpis['total_tax'] = fk.get('total_tax') or 0.0
        if fk.get('document_count'):
            # Do not override invoices/bills split; filing document_count is GSTR-1 docs.
            overview_kpis['filing_document_count'] = fk.get('document_count')
        if fk.get('credit_note_count') is not None:
            overview_kpis['total_credit_notes'] = fk.get('credit_note_count') or overview_kpis['total_credit_notes']
        if fk.get('debit_note_count') is not None:
            overview_kpis['total_debit_notes'] = fk.get('debit_note_count') or overview_kpis['total_debit_notes']
    else:
        overview_kpis.setdefault('cgst', 0.0)
        overview_kpis.setdefault('sgst', 0.0)
        overview_kpis.setdefault('igst', 0.0)
        overview_kpis.setdefault('cess', 0.0)

    overview = empty_section('overview', available=True)
    overview['kpis'] = overview_kpis

    tax_summary = empty_section('tax_summary', available=True)
    tax_summary['kpis'] = {
        'taxable_value': overview_kpis.get('taxable_value') or 0.0,
        'cgst': overview_kpis.get('cgst') or 0.0,
        'sgst': overview_kpis.get('sgst') or 0.0,
        'igst': overview_kpis.get('igst') or 0.0,
        'cess': overview_kpis.get('cess') or 0.0,
        'total_tax': overview_kpis.get('total_tax') or 0.0,
        'source': 'filing' if filing.get('available') and filing.get('kpis', {}).get('total_tax') else 'account.move',
    }

    return {
        'overview': overview,
        'filing': filing,
        'reconciliation_2b': recon,
        'invoice_validation': validation,
        'itc': itc,
        'einvoice': einvoice,
        'ewaybill': ewaybill,
        'exceptions': exceptions,
        'tax_summary': tax_summary,
        'trends': empty_section('trends', available=True, message='Trends not implemented yet.'),
        'action_items': [],
        'module_availability': availability,
        'filters': filters,
    }
