# -*- coding: utf-8 -*-
from decimal import Decimal, ROUND_HALF_UP

from odoo import api, models, _
from odoo.exceptions import UserError, ValidationError


class ArmoraGstItcUtilization(models.AbstractModel):
    """Versioned ITC utilization engine.

    Does not invent a hard-coded “new” ITC rule. Resolves ITC_UTILIZATION
    rule configuration for the filing period and applies priority steps.
    Illegal cross-utilization (e.g. CESS to GST heads) is rejected.
    """

    _name = 'armora.gst.itc.utilization'
    _description = 'Armora GST ITC Utilization'

    HEADS = ('igst', 'cgst', 'sgst', 'cess')

    @api.model
    def _money(self, amount):
        return Decimal(str(amount or 0)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    @api.model
    def _resolve_rule(self, on_date=None, return_period=None):
        rule = self.env['armora.gst.rule'].find_applicable(
            'ITC_UTILIZATION',
            on_date=on_date,
            return_period=return_period,
        )
        if not rule:
            raise UserError(_('No ITC_UTILIZATION rule found for the period.'))
        return rule

    @api.model
    def utilize(self, vals):
        """
        vals:
          on_date / return_period
          opening_itc: {igst,cgst,sgst,cess}
          itc_available: {igst,cgst,sgst,cess}  (credits of period; optional, added to opening)
          liabilities: {igst,cgst,sgst,cess}
        """
        data = vals or {}
        rule = self._resolve_rule(on_date=data.get('on_date'), return_period=data.get('return_period'))
        cfg = rule.get_config()
        priority = list(cfg.get('priority') or [])
        allow_cgst_sgst_to_igst = bool(cfg.get('allow_cgst_sgst_to_igst_after_igst_itc'))

        opening = {h: self._money((data.get('opening_itc') or {}).get(h)) for h in self.HEADS}
        available_in = {h: self._money((data.get('itc_available') or {}).get(h)) for h in self.HEADS}
        liability = {h: self._money((data.get('liabilities') or {}).get(h)) for h in self.HEADS}

        itc = {h: opening[h] + available_in[h] for h in self.HEADS}
        remaining_liability = dict(liability)
        utilized = {h: self._money(0) for h in self.HEADS}
        steps = []

        def apply_step(from_head, to_head):
            if from_head == 'cess' and to_head != 'cess':
                raise ValidationError(_('Illegal ITC cross-utilization: CESS cannot settle %s.') % to_head.upper())
            if to_head == 'cess' and from_head != 'cess':
                raise ValidationError(_('Illegal ITC cross-utilization: %s cannot settle CESS.') % from_head.upper())
            # Classic restrictions unless version allows CGST/SGST -> IGST after IGST ITC exhausted
            if from_head in ('cgst', 'sgst') and to_head == 'igst' and not allow_cgst_sgst_to_igst:
                raise ValidationError(_(
                    'ITC rule version %(ver)s does not allow %(frm)s ITC against IGST liability.',
                    ver=rule.version,
                    frm=from_head.upper(),
                ))
            if from_head == 'cgst' and to_head == 'sgst':
                raise ValidationError(_('CGST ITC cannot be used against SGST liability.'))
            if from_head == 'sgst' and to_head == 'cgst':
                raise ValidationError(_('SGST ITC cannot be used against CGST liability.'))

            amount = min(itc[from_head], remaining_liability[to_head])
            if amount <= 0:
                return
            itc[from_head] -= amount
            remaining_liability[to_head] -= amount
            utilized[from_head] += amount
            steps.append({
                'from': from_head,
                'to': to_head,
                'amount': float(amount),
            })

        mapping = {
            'igst_itc_to_igst': ('igst', 'igst'),
            'igst_itc_to_cgst': ('igst', 'cgst'),
            'igst_itc_to_sgst': ('igst', 'sgst'),
            'cgst_itc_to_cgst': ('cgst', 'cgst'),
            'sgst_itc_to_sgst': ('sgst', 'sgst'),
            'cgst_itc_to_igst': ('cgst', 'igst'),
            'sgst_itc_to_igst': ('sgst', 'igst'),
            'cess_itc_to_cess': ('cess', 'cess'),
        }

        # If flexible CGST/SGST->IGST is enabled, only after IGST ITC is exhausted for IGST liability
        for key in priority:
            pair = mapping.get(key)
            if not pair:
                continue
            frm, to = pair
            if key in ('cgst_itc_to_igst', 'sgst_itc_to_igst'):
                if not allow_cgst_sgst_to_igst:
                    continue
                if itc['igst'] > 0 and remaining_liability['igst'] > 0:
                    # Still have IGST ITC that could settle IGST; skip until exhausted
                    continue
            apply_step(frm, to)

        cash_payable = {h: float(remaining_liability[h]) for h in self.HEADS}
        return {
            'rule_version': rule.version,
            'rule_id': rule.id,
            'opening_itc': {h: float(opening[h]) for h in self.HEADS},
            'itc_available': {h: float(available_in[h]) for h in self.HEADS},
            'itc_utilized': {h: float(utilized[h]) for h in self.HEADS},
            'itc_remaining': {h: float(itc[h]) for h in self.HEADS},
            'cash_payable': cash_payable,
            'steps': steps,
            'configuration': cfg,
        }
