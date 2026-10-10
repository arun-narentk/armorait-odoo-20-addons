# -*- coding: utf-8 -*-
"""Indian financial year and GST return period utilities."""

from __future__ import annotations

import calendar
from datetime import date

from ..exceptions import GstPeriodError


def _as_date(value):
    if value is None or value is False:
        return date.today()
    if isinstance(value, date):
        return value
    raise GstPeriodError('Expected a date value for period calculation.')


def get_financial_year(on_date=None):
    """Return Indian FY label like ``2025-26`` (April to March)."""
    on_date = _as_date(on_date)
    start = on_date.year if on_date.month >= 4 else on_date.year - 1
    return '%s-%s' % (start, str(start + 1)[-2:])


def fy_start_year(financial_year):
    """Parse ``2025-26`` -> ``2025``."""
    text = (financial_year or '').strip()
    if not text or '-' not in text:
        raise GstPeriodError('Financial year must look like 2025-26.')
    try:
        return int(text.split('-')[0])
    except ValueError as err:
        raise GstPeriodError('Invalid financial year: %s' % financial_year) from err


def normalize_return_month(return_period):
    """Normalize monthly period to ``01``..``12``."""
    period = (return_period or '').strip()
    if not period.isdigit() or not (1 <= int(period) <= 12):
        raise GstPeriodError('Monthly return period must be 01 to 12.')
    return '%02d' % int(period)


def get_return_period(on_date=None, frequency='monthly'):
    """Return period label for a date: ``08`` (monthly) or ``Q2`` (quarterly)."""
    on_date = _as_date(on_date)
    frequency = (frequency or 'monthly').strip().lower()
    if frequency == 'monthly':
        return '%02d' % on_date.month
    if frequency == 'quarterly':
        # Indian FY quarters: Apr-Jun Q1, Jul-Sep Q2, Oct-Dec Q3, Jan-Mar Q4
        if on_date.month in (4, 5, 6):
            return 'Q1'
        if on_date.month in (7, 8, 9):
            return 'Q2'
        if on_date.month in (10, 11, 12):
            return 'Q3'
        return 'Q4'
    raise GstPeriodError('Frequency must be monthly or quarterly.')


def get_period_start(financial_year, return_period, frequency='monthly'):
    """Return the first date of a GST return period."""
    start, _end = compute_period_dates(financial_year, return_period, frequency)
    return start


def get_period_end(financial_year, return_period, frequency='monthly'):
    """Return the last date of a GST return period."""
    _start, end = compute_period_dates(financial_year, return_period, frequency)
    return end


def compute_period_dates(financial_year, return_period, frequency='monthly'):
    """Return ``(period_start, period_end)`` for monthly or quarterly periods."""
    start_year = fy_start_year(financial_year)
    frequency = (frequency or 'monthly').strip().lower()
    period = (return_period or '').strip().upper()

    if frequency == 'monthly':
        month = int(normalize_return_month(period))
        year = start_year if month >= 4 else start_year + 1
        last = calendar.monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last)

    if frequency == 'quarterly':
        quarters = {
            'Q1': (4, start_year, 6, start_year),
            'Q2': (7, start_year, 9, start_year),
            'Q3': (10, start_year, 12, start_year),
            'Q4': (1, start_year + 1, 3, start_year + 1),
            '1': (4, start_year, 6, start_year),
            '2': (7, start_year, 9, start_year),
            '3': (10, start_year, 12, start_year),
            '4': (1, start_year + 1, 3, start_year + 1),
        }
        if period not in quarters:
            raise GstPeriodError('Quarterly return period must be Q1 to Q4.')
        sm, sy, em, ey = quarters[period]
        return date(sy, sm, 1), date(ey, em, calendar.monthrange(ey, em)[1])

    raise GstPeriodError('Frequency must be monthly or quarterly.')
