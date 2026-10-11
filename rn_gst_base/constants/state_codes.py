# -*- coding: utf-8 -*-
"""Official GST state TIN codes (codes only, not state names).

Primary resolution of state records should use Odoo ``res.country.state``
with ``l10n_in_tin``. This set is used for format/membership checks without
hard-coding state display names.
"""

# Special GST codes used by Odoo l10n_in / GSTN conventions.
TIN_FOREIGN_COUNTRY = '96'
TIN_OTHER_TERRITORY = '97'

# Official GST state/UT TIN codes commonly used with Indian GSTIN prefix.
# Kept as codes only. Names come from Odoo country/state masters.
OFFICIAL_GST_TIN_CODES = frozenset({
    '01', '02', '03', '04', '05', '06', '07', '08', '09', '10',
    '11', '12', '13', '14', '15', '16', '17', '18', '19', '20',
    '21', '22', '23', '24', '25', '26', '27', '28', '29', '30',
    '31', '32', '33', '34', '35', '36', '37', '38',
    TIN_FOREIGN_COUNTRY,
    TIN_OTHER_TERRITORY,
})
