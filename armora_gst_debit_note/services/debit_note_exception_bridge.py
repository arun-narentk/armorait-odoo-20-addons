# -*- coding: utf-8 -*-
"""Soft bridge to armora_gst_exception when installed."""


def exception_module_installed(env):
    return bool(env['ir.module.module'].sudo().search_count([
        ('name', '=', 'armora_gst_exception'),
        ('state', '=', 'installed'),
    ]))


def post_exceptions(env, findings):
    """Map debit-note findings to exceptions. Implemented in Prompt 17."""
    if not exception_module_installed(env):
        return False
    del findings
    return False
