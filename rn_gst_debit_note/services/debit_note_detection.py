# -*- coding: utf-8 -*-
"""Detect GST debit notes on account.move via debit_origin_id."""


def is_debit_note(move):
    """Return True when the move is an Odoo debit note (not a credit note)."""
    return bool(getattr(move, 'debit_origin_id', False))


def is_customer_debit_note(move):
    return is_debit_note(move) and move.move_type == 'out_invoice'


def is_vendor_debit_note(move):
    return is_debit_note(move) and move.move_type == 'in_invoice'


def is_gst_document_candidate(move):
    """True when the move looks like a GST debit note document (taxes may still be empty)."""
    return is_debit_note(move) and move.move_type in ('out_invoice', 'in_invoice')
