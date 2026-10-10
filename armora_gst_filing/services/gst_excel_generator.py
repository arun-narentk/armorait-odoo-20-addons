# -*- coding: utf-8 -*-
"""GSTN Offline Tool Excel generation service facade.

Implementation: ``armora.gst.excel.generator`` (models/gst_excel_generator.py).
"""


def generate(env, filing):
    """Populate the official Offline Tool workbook for a filing."""
    return env['armora.gst.excel.generator'].generate(filing)
