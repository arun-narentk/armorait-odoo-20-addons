# -*- coding: utf-8 -*-
"""GST classification service facade.

Implementation: ``armora.gst.classification`` (models/gst_classification.py).
"""


def classify_move_line(env, move, move_line, company=None):
    """Classify one invoice line for GSTR-1 table placement."""
    return env['armora.gst.classification'].classify_move_line(
        move, move_line, company=company
    )
