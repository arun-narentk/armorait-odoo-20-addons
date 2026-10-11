# -*- coding: utf-8 -*-
"""Rows of the GSTR-9C reconciliation statement.

Same layout as gstr9_rows: (code, part, table, label, kind, source).
  kind:   'value' one amount, 'itc' the four tax heads, 'tax' amount and the four heads
  source: 'books' (ledger), 'gstr9' (the year's GSTR-9), 'computed', 'manual'
Rate-wise liability (Table 9) and expense-wise ITC (Table 14) are separate lines.
"""

ROWS = [
    # Part II: reconciliation of turnover (Table 5)
    ('5A', '2', '5', 'Turnover (including exports) as per audited financial statements', 'value', 'books'),
    ('5B', '2', '5', 'Unbilled revenue at the beginning of the financial year (+)', 'value', 'manual'),
    ('5C', '2', '5', 'Unadjusted advances at the end of the financial year (+)', 'value', 'manual'),
    ('5D', '2', '5', 'Deemed supply under Schedule I (+)', 'value', 'manual'),
    ('5E', '2', '5', 'Credit notes issued after the end of the year but reflected in the annual return (+)', 'value', 'manual'),
    ('5F', '2', '5', 'Trade discounts accounted for in the financial statements but not permissible under GST (+)', 'value', 'manual'),
    ('5H', '2', '5', 'Unbilled revenue at the end of the financial year (-)', 'value', 'manual'),
    ('5I', '2', '5', 'Unadjusted advances at the beginning of the financial year (-)', 'value', 'manual'),
    ('5J', '2', '5', 'Credit notes accounted for in the financial statements but not permissible under GST (-)', 'value', 'manual'),
    ('5K', '2', '5', 'Adjustments on account of supply of goods by SEZ units to DTA units (-)', 'value', 'manual'),
    ('5L', '2', '5', 'Turnover for the period under composition scheme (-)', 'value', 'manual'),
    ('5M', '2', '5', 'Adjustments in turnover under section 15 and rules thereunder (+/-)', 'value', 'manual'),
    ('5N', '2', '5', 'Adjustments in turnover due to foreign exchange fluctuations (+/-)', 'value', 'manual'),
    ('5O', '2', '5', 'Adjustments in turnover due to reasons not listed above (+/-)', 'value', 'manual'),
    ('5P', '2', '5', 'Annual turnover after adjustments as above', 'value', 'computed'),
    ('5Q', '2', '5', 'Turnover as declared in the annual return (GSTR-9)', 'value', 'gstr9'),
    ('5R', '2', '5', 'Unreconciled turnover (Q - P)', 'value', 'computed'),
    # Part II: reconciliation of taxable turnover (Table 7)
    ('7A', '2', '7', 'Annual turnover after adjustments (from 5P above)', 'value', 'computed'),
    ('7B', '2', '7', 'Value of exempted, nil rated, non-GST supplies and no-supply turnover', 'value', 'gstr9'),
    ('7C', '2', '7', 'Zero rated supplies without payment of tax', 'value', 'gstr9'),
    ('7D', '2', '7', 'Supplies on which tax is to be paid by the recipient on reverse charge basis', 'value', 'gstr9'),
    ('7E', '2', '7', 'Taxable turnover as per adjustments above (A - B - C - D)', 'value', 'computed'),
    ('7F', '2', '7', 'Taxable turnover as per liability declared in the annual return (GSTR-9)', 'value', 'gstr9'),
    ('7G', '2', '7', 'Unreconciled taxable turnover (F - E)', 'value', 'computed'),
    # Part III: reconciliation of tax paid (Table 9; rate-wise lines are separate)
    ('9J', '3', '9', 'Interest', 'itc', 'manual'),
    ('9K', '3', '9', 'Late fee', 'itc', 'manual'),
    ('9L', '3', '9', 'Penalty', 'itc', 'manual'),
    ('9M', '3', '9', 'Others', 'itc', 'manual'),
    ('9N', '3', '9', 'Total amount to be paid as per the rate-wise lines and rows above', 'tax', 'computed'),
    ('9O', '3', '9', 'Total amount paid as declared in the annual return (GSTR-9 Table 9)', 'itc', 'gstr9'),
    ('9P', '3', '9', 'Unpaid amount (N - O)', 'itc', 'computed'),
    ('11', '3', '11', 'Additional amount payable but not paid (due to reasons in Table 10)', 'tax', 'manual'),
    # Part IV: reconciliation of input tax credit (Table 12)
    ('12A', '4', '12', 'ITC availed as per audited financial statements (input tax booked in the ledger)', 'value', 'books'),
    ('12B', '4', '12', 'ITC booked in earlier financial years claimed in the current year (+)', 'value', 'manual'),
    ('12C', '4', '12', 'ITC booked in the current year to be claimed in subsequent years (-)', 'value', 'manual'),
    ('12D', '4', '12', 'ITC availed as per audited financial statements (A + B - C)', 'value', 'computed'),
    ('12E', '4', '12', 'ITC claimed in the annual return (GSTR-9 7J)', 'value', 'gstr9'),
    ('12F', '4', '12', 'Unreconciled ITC (E - D)', 'value', 'computed'),
    # Part IV: ITC on expenses (Table 14; expense-wise lines are separate)
    ('14R', '4', '14', 'Total ITC eligible on expenses as per books (sum of the expense-wise lines)', 'value', 'books'),
    ('14S', '4', '14', 'ITC claimed in the annual return (GSTR-9 7J)', 'value', 'gstr9'),
    ('14T', '4', '14', 'Unreconciled ITC (S - R)', 'value', 'computed'),
    ('16', '4', '16', 'Tax payable on unreconciled difference in ITC', 'itc', 'manual'),
]

ROW_INFO = {row[0]: row for row in ROWS}

TOTALS = {
    '5P': [(1, '5A'), (1, '5B'), (1, '5C'), (1, '5D'), (1, '5E'), (1, '5F'),
           (-1, '5H'), (-1, '5I'), (-1, '5J'), (-1, '5K'), (-1, '5L'), (1, '5M'), (1, '5N'), (1, '5O')],
    '5R': [(1, '5Q'), (-1, '5P')],
    '7A': [(1, '5P')],
    '7E': [(1, '7A'), (-1, '7B'), (-1, '7C'), (-1, '7D')],
    '7G': [(1, '7F'), (-1, '7E')],
    '9N': [(1, '9J'), (1, '9K'), (1, '9L'), (1, '9M')],  # plus the rate-wise lines
    '9P': [(1, '9N'), (-1, '9O')],
    '12D': [(1, '12A'), (1, '12B'), (-1, '12C')],
    '12F': [(1, '12E'), (-1, '12D')],
    '14T': [(1, '14S'), (-1, '14R')],
}
TOTAL_ORDER = ['5P', '5R', '7A', '7E', '7G', '9N', '9P', '12D', '12F', '14T']

PARTS = [
    ('2', 'Part II: Reconciliation of turnover'),
    ('3', 'Part III: Reconciliation of tax paid'),
    ('4', 'Part IV: Reconciliation of input tax credit'),
]
