# -*- coding: utf-8 -*-
"""Shared filter helpers for dashboard providers."""


def normalize_filters(filters):
    filters = dict(filters or {})
    gstin = filters.get('gstin') or False
    if gstin:
        gstin = str(gstin).upper().strip()
    filters['gstin'] = gstin or False
    return filters


def company_id(filters):
    return filters.get('company_id') or False


def period_domain_keys(filters, gstin_field='gstin'):
    """Common company / GSTIN / FY / return-period domain fragment."""
    domain = []
    cid = company_id(filters)
    if cid:
        domain.append(('company_id', '=', cid))
    if filters.get('gstin') and gstin_field:
        domain.append((gstin_field, '=', filters['gstin']))
    if filters.get('financial_year'):
        domain.append(('financial_year', '=', filters['financial_year']))
    if filters.get('return_period'):
        domain.append(('return_period', '=', filters['return_period']))
    return domain


def move_period_domain(filters):
    """account.move domain for the selected company and invoice date range."""
    domain = [
        ('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')),
        ('state', '=', 'posted'),
    ]
    cid = company_id(filters)
    if cid:
        domain.append(('company_id', '=', cid))
    if filters.get('date_from'):
        domain.append(('invoice_date', '>=', filters['date_from']))
    if filters.get('date_to'):
        domain.append(('invoice_date', '<=', filters['date_to']))
    # Prefer Indian localization documents when the field exists.
    return domain
