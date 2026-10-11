# -*- coding: utf-8 -*-
"""GST filing validation service facade.

Implementation: ``rn.gst.filing.validation`` (models/gst_validation.py).
"""


def validate_filing(env, filing):
    """Run filing validation and write result lines."""
    return env['rn.gst.filing.validation'].validate_filing(filing)
