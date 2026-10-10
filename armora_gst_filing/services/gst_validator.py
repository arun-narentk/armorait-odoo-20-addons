# -*- coding: utf-8 -*-
"""GST filing validation service facade.

Implementation: ``armora.gst.filing.validation`` (models/gst_validation.py).
"""


def validate_filing(env, filing):
    """Run filing validation and write result lines."""
    return env['armora.gst.filing.validation'].validate_filing(filing)
