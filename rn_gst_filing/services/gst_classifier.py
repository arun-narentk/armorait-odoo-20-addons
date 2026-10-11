# -*- coding: utf-8 -*-
"""GST classification service facade.

Implementation: ``rn.gst.classification`` (models/gst_classification.py).
"""


def classify_move_line(env, move, move_line, company=None):
    """Classify one invoice line for GSTR-1 table placement."""
    return env['rn.gst.classification'].classify_move_line(
        move, move_line, company=company
    )
