# -*- coding: utf-8 -*-
"""GST data extraction service facade.

Implementation: ``rn.gst.data.extractor`` (models/gst_data_extractor.py).
"""


def extract_to_filing(env, filing, regenerate=False):
    """Load posted GST documents into a filing snapshot."""
    return env['rn.gst.data.extractor'].extract_to_filing(filing, regenerate=regenerate)
