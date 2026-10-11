# -*- coding: utf-8 -*-
"""Rows of the GSTR-9 annual return.

Each row: (code, part, table, label, kind, source)
  kind:   'tax'   taxable value and the four tax heads
          'value' taxable value only
          'itc'   the four tax heads only
          'pay'   Table 9 / 14: tax payable (value), paid in cash, paid through ITC by credit head
  source: 'books'    filled from posted invoices and bills
          'gstr3b'   summed from the year's GSTR-3B records
          'gstr2b'   summed from the year's GSTR-2B reconciliations
          'computed' a total of other rows (see TOTALS)
          'manual'   entered by hand and kept when the return is filled again
"""

ROWS = [
    # Part II: outward and inward supplies on which tax is payable (Table 4)
    ('4A', '2', '4', 'Supplies made to unregistered persons (B2C)', 'tax', 'books'),
    ('4B', '2', '4', 'Supplies made to registered persons (B2B)', 'tax', 'books'),
    ('4C', '2', '4', 'Zero rated supply (export) on payment of tax (except supplies to SEZs)', 'tax', 'books'),
    ('4D', '2', '4', 'Supply to SEZs on payment of tax', 'tax', 'books'),
    ('4E', '2', '4', 'Deemed exports', 'tax', 'books'),
    ('4F', '2', '4', 'Advances on which tax has been paid but invoice has not been issued', 'tax', 'manual'),
    ('4G', '2', '4', 'Inward supplies on which tax is to be paid on reverse charge basis', 'tax', 'books'),
    ('4H', '2', '4', 'Sub-total (A to G above)', 'tax', 'computed'),
    ('4I', '2', '4', 'Credit notes issued in respect of transactions in (B) to (E) above (-)', 'tax', 'books'),
    ('4J', '2', '4', 'Debit notes issued in respect of transactions in (B) to (E) above (+)', 'tax', 'books'),
    ('4K', '2', '4', 'Supplies / tax declared through amendments (+)', 'tax', 'manual'),
    ('4L', '2', '4', 'Supplies / tax reduced through amendments (-)', 'tax', 'manual'),
    ('4M', '2', '4', 'Sub-total (I to L above)', 'tax', 'computed'),
    ('4N', '2', '4', 'Supplies and advances on which tax is to be paid (H + M above)', 'tax', 'computed'),
    # Part II: outward supplies on which tax is not payable (Table 5)
    ('5A', '2', '5', 'Zero rated supply (export) without payment of tax', 'value', 'books'),
    ('5B', '2', '5', 'Supply to SEZs without payment of tax', 'value', 'books'),
    ('5C', '2', '5', 'Supplies on which tax is to be paid by the recipient on reverse charge basis', 'value', 'books'),
    ('5D', '2', '5', 'Exempted', 'value', 'books'),
    ('5E', '2', '5', 'Nil rated', 'value', 'books'),
    ('5F', '2', '5', 'Non-GST supply (includes no supply)', 'value', 'books'),
    ('5G', '2', '5', 'Sub-total (A to F above)', 'value', 'computed'),
    ('5H', '2', '5', 'Credit notes issued in respect of transactions in A to F above (-)', 'value', 'books'),
    ('5I', '2', '5', 'Debit notes issued in respect of transactions in A to F above (+)', 'value', 'books'),
    ('5J', '2', '5', 'Supplies declared through amendments (+)', 'value', 'manual'),
    ('5K', '2', '5', 'Supplies reduced through amendments (-)', 'value', 'manual'),
    ('5L', '2', '5', 'Sub-total (H to K above)', 'value', 'computed'),
    ('5M', '2', '5', 'Turnover on which tax is not to be paid (G + L above)', 'value', 'computed'),
    ('5N', '2', '5', 'Total turnover including advances (4N + 5M - 4G above)', 'value', 'computed'),
    # Part III: ITC availed (Table 6)
    ('6A', '3', '6', 'Total ITC availed through GSTR-3B (sum of Table 4A of GSTR-3B)', 'itc', 'gstr3b'),
    ('6B1', '3', '6', 'Inward supplies (other than imports and reverse charge): inputs', 'itc', 'books'),
    ('6B2', '3', '6', 'Inward supplies (other than imports and reverse charge): capital goods', 'itc', 'books'),
    ('6B3', '3', '6', 'Inward supplies (other than imports and reverse charge): input services', 'itc', 'books'),
    ('6C', '3', '6', 'Inward supplies from unregistered persons under reverse charge, tax paid and ITC availed', 'itc', 'books'),
    ('6D', '3', '6', 'Inward supplies from registered persons under reverse charge, tax paid and ITC availed', 'itc', 'books'),
    ('6E', '3', '6', 'Import of goods (including supplies from SEZs)', 'itc', 'books'),
    ('6F', '3', '6', 'Import of services (excluding inward supplies from SEZs)', 'itc', 'books'),
    ('6G', '3', '6', 'Input tax credit received from ISD', 'itc', 'gstr3b'),
    ('6H', '3', '6', 'Amount of ITC reclaimed (other than B above)', 'itc', 'gstr3b'),
    ('6I', '3', '6', 'Sub-total (B to H above)', 'itc', 'computed'),
    ('6J', '3', '6', 'Difference (I - A above)', 'itc', 'computed'),
    ('6K', '3', '6', 'Transition credit through TRAN-I (including revisions)', 'itc', 'manual'),
    ('6L', '3', '6', 'Transition credit through TRAN-II', 'itc', 'manual'),
    ('6M', '3', '6', 'Any other ITC availed but not specified above', 'itc', 'manual'),
    ('6N', '3', '6', 'Sub-total (K to M above)', 'itc', 'computed'),
    ('6O', '3', '6', 'Total ITC availed (I + N above)', 'itc', 'computed'),
    # Part III: ITC reversed (Table 7)
    ('7A', '3', '7', 'As per Rule 37', 'itc', 'manual'),
    ('7B', '3', '7', 'As per Rule 39', 'itc', 'manual'),
    ('7C', '3', '7', 'As per Rule 42', 'itc', 'manual'),
    ('7D', '3', '7', 'As per Rule 43', 'itc', 'manual'),
    ('7E', '3', '7', 'As per section 17(5) (GSTR-3B 4(B)(1), which also covers rules 38, 42 and 43)', 'itc', 'gstr3b'),
    ('7F', '3', '7', 'Reversal of TRAN-I credit', 'itc', 'manual'),
    ('7G', '3', '7', 'Reversal of TRAN-II credit', 'itc', 'manual'),
    ('7H', '3', '7', 'Other reversals (GSTR-3B 4(B)(2))', 'itc', 'gstr3b'),
    ('7I', '3', '7', 'Total ITC reversed (A to H above)', 'itc', 'computed'),
    ('7J', '3', '7', 'Net ITC available for utilization (6O - 7I)', 'itc', 'computed'),
    # Part III: other ITC information (Table 8)
    ('8A', '3', '8', 'ITC as per GSTR-2B (Tables 3 and 5 thereof)', 'itc', 'gstr2b'),
    ('8B', '3', '8', 'ITC as per sum of 6(B) and 6(H) above', 'itc', 'computed'),
    ('8C', '3', '8', 'ITC on inward supplies received during the year but availed in the next year', 'itc', 'manual'),
    ('8D', '3', '8', 'Difference [A - (B + C)]', 'itc', 'computed'),
    ('8E', '3', '8', 'ITC available but not availed', 'itc', 'manual'),
    ('8F', '3', '8', 'ITC available but ineligible', 'itc', 'manual'),
    ('8G', '3', '8', 'IGST paid on import of goods (including supplies from SEZ), as booked on import bills', 'itc', 'books'),
    ('8H', '3', '8', 'IGST credit availed on import of goods (as per 6(E) above)', 'itc', 'computed'),
    ('8I', '3', '8', 'Difference (G - H)', 'itc', 'computed'),
    ('8J', '3', '8', 'ITC available but not availed on import of goods (equal to I)', 'itc', 'computed'),
    ('8K', '3', '8', 'Total ITC to be lapsed in current financial year (E + F + J)', 'itc', 'computed'),
    # Part IV: tax paid (Table 9)
    ('9IGST', '4', '9', 'Integrated Tax', 'pay', 'gstr3b'),
    ('9CGST', '4', '9', 'Central Tax', 'pay', 'gstr3b'),
    ('9SGST', '4', '9', 'State/UT Tax', 'pay', 'gstr3b'),
    ('9CESS', '4', '9', 'Cess', 'pay', 'gstr3b'),
    ('9INT', '4', '9', 'Interest', 'pay', 'gstr3b'),
    ('9FEE', '4', '9', 'Late fee', 'pay', 'manual'),
    ('9PEN', '4', '9', 'Penalty', 'pay', 'manual'),
    ('9OTH', '4', '9', 'Other', 'pay', 'manual'),
    # Part V: transactions of this year declared in returns of April to September of the next year
    ('10', '5', '10', 'Supplies / tax declared through amendments (+) (net of debit notes)', 'tax', 'manual'),
    ('11', '5', '11', 'Supplies / tax reduced through amendments (-) (net of credit notes)', 'tax', 'manual'),
    ('12', '5', '12', 'Reversal of ITC availed during previous financial year', 'itc', 'manual'),
    ('13', '5', '13', 'ITC availed for the previous financial year', 'itc', 'manual'),
    ('14IGST', '5', '14', 'Differential tax paid: Integrated Tax', 'pay', 'manual'),
    ('14CGST', '5', '14', 'Differential tax paid: Central Tax', 'pay', 'manual'),
    ('14SGST', '5', '14', 'Differential tax paid: State/UT Tax', 'pay', 'manual'),
    ('14CESS', '5', '14', 'Differential tax paid: Cess', 'pay', 'manual'),
    ('14INT', '5', '14', 'Differential tax paid: Interest', 'pay', 'manual'),
    # Part VI: other information
    ('15A', '6', '15', 'Total refund claimed', 'itc', 'manual'),
    ('15B', '6', '15', 'Total refund sanctioned', 'itc', 'manual'),
    ('15C', '6', '15', 'Total refund rejected', 'itc', 'manual'),
    ('15D', '6', '15', 'Total refund pending', 'itc', 'manual'),
    ('15E', '6', '15', 'Total demand of taxes', 'itc', 'manual'),
    ('15F', '6', '15', 'Total taxes paid in respect of E above', 'itc', 'manual'),
    ('15G', '6', '15', 'Total demands pending out of E above', 'itc', 'manual'),
    ('16A', '6', '16', 'Supplies received from composition taxpayers', 'value', 'books'),
    ('16B', '6', '16', 'Deemed supply under section 143', 'tax', 'manual'),
    ('16C', '6', '16', 'Goods sent on approval basis but not returned', 'tax', 'manual'),
    ('19', '6', '19', 'Late fee payable and paid', 'itc', 'manual'),
]

ROW_INFO = {row[0]: row for row in ROWS}

# Totals, recomputed after every fill and edit: code -> [(sign, code), ...]
TOTALS = {
    '4H': [(1, c) for c in ('4A', '4B', '4C', '4D', '4E', '4F', '4G')],
    '4M': [(-1, '4I'), (1, '4J'), (1, '4K'), (-1, '4L')],
    '4N': [(1, '4H'), (1, '4M')],
    '5G': [(1, c) for c in ('5A', '5B', '5C', '5D', '5E', '5F')],
    '5L': [(-1, '5H'), (1, '5I'), (1, '5J'), (-1, '5K')],
    '5M': [(1, '5G'), (1, '5L')],
    '5N': [(1, '4N'), (1, '5M'), (-1, '4G')],
    '6I': [(1, c) for c in ('6B1', '6B2', '6B3', '6C', '6D', '6E', '6F', '6G', '6H')],
    '6J': [(1, '6I'), (-1, '6A')],
    '6N': [(1, '6K'), (1, '6L'), (1, '6M')],
    '6O': [(1, '6I'), (1, '6N')],
    '7I': [(1, c) for c in ('7A', '7B', '7C', '7D', '7E', '7F', '7G', '7H')],
    '7J': [(1, '6O'), (-1, '7I')],
    '8B': [(1, '6B1'), (1, '6B2'), (1, '6B3'), (1, '6H')],
    '8D': [(1, '8A'), (-1, '8B'), (-1, '8C')],
    '8H': [(1, '6E')],
    '8I': [(1, '8G'), (-1, '8H')],
    '8J': [(1, '8I')],
    '8K': [(1, '8E'), (1, '8F'), (1, '8J')],
}
# Totals are listed in an order where every total comes after the rows it uses.
TOTAL_ORDER = ['4H', '4M', '4N', '5G', '5L', '5M', '5N', '6I', '6J', '6N', '6O', '7I', '7J',
               '8B', '8D', '8H', '8I', '8J', '8K']

PARTS = [
    ('2', 'Part II: Outward and inward supplies'),
    ('3', 'Part III: Input tax credit'),
    ('4', 'Part IV: Tax paid'),
    ('5', 'Part V: Previous year transactions declared next year'),
    ('6', 'Part VI: Other information'),
]
