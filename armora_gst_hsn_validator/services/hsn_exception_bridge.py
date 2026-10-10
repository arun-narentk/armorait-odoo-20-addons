# -*- coding: utf-8 -*-
"""Soft bridge to ``armora_gst_exception`` when that module is installed.

HSN validator must remain usable if the exception center is absent.
"""


def exception_module_installed(env):
    return bool(env['ir.module.module'].sudo().search_count([
        ('name', '=', 'armora_gst_exception'),
        ('state', '=', 'installed'),
    ]))


def post_exceptions(env, results):
    """Map validation results to exceptions. Implemented in Prompt 11."""
    if not exception_module_installed(env):
        return False
    del results
    return False
