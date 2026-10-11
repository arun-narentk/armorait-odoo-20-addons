# -*- coding: utf-8 -*-
"""Soft bridge to rn_gst_exception when installed."""


def exception_module_installed(env):
    return bool(env['ir.module.module'].sudo().search_count([
        ('name', '=', 'rn_gst_exception'),
        ('state', '=', 'installed'),
    ]))


def post_exceptions(env, findings):
    """Map rate conflicts to exceptions. Implemented in Prompt 15."""
    if not exception_module_installed(env):
        return False
    del findings
    return False
