# -*- coding: utf-8 -*-
"""Phase 1 sales analytics tools (read-only)."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from odoo import fields

from .base import BaseAITool
from .registry import register_tool
from .result import error_result, tool_result


@register_tool
class TodaySalesTool(BaseAITool):
    name = 'today_sales'
    description = "Show confirmed sales orders and revenue for today."

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        SaleOrder = self.env['sale.order']
        SaleOrder.check_access('read')
        today = fields.Date.today()
        orders = SaleOrder.search([
            ('date_order', '>=', today),
            ('date_order', '<', today + timedelta(days=1)),
            ('state', 'in', ('sale', 'done')),
        ])
        revenue = sum(orders.mapped('amount_total'))
        currency = self.env.company.currency_id.name
        return tool_result(
            headline=f"{len(orders)} sales orders today",
            summary=f"Today's sales: {len(orders)} orders totaling {revenue:.2f} {currency}.",
            model='sale.order',
            domain=[
                ('date_order', '>=', today),
                ('date_order', '<', today + timedelta(days=1)),
                ('state', 'in', ('sale', 'done')),
            ],
            record_ids=orders.ids,
            metrics=[
                {'label': 'Orders', 'value': len(orders)},
                {'label': 'Revenue', 'value': f'{revenue:.2f} {currency}'},
            ],
            category='sales',
        )


@register_tool
class PendingQuotationsTool(BaseAITool):
    name = 'pending_quotations'
    description = 'List draft or sent quotations still waiting for confirmation.'

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        limit = min(int(arguments.get('limit') or 20), 50)
        SaleOrder = self.env['sale.order']
        SaleOrder.check_access('read')
        orders = SaleOrder.search([
            ('state', 'in', ('draft', 'sent')),
        ], limit=limit, order='date_order desc')
        total = sum(orders.mapped('amount_total'))
        return tool_result(
            headline=f'{len(orders)} pending quotations',
            summary=f'{len(orders)} quotations waiting for confirmation, totaling {total:.2f}.',
            model='sale.order',
            domain=[('state', 'in', ('draft', 'sent'))],
            record_ids=orders.ids,
            category='sales',
        )


@register_tool
class LostQuotationsTool(BaseAITool):
    name = 'lost_quotations'
    description = 'List cancelled quotations.'

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        limit = min(int(arguments.get('limit') or 20), 50)
        SaleOrder = self.env['sale.order']
        SaleOrder.check_access('read')
        orders = SaleOrder.search([('state', '=', 'cancel')], limit=limit, order='date_order desc')
        return tool_result(
            headline=f'{len(orders)} lost quotations',
            summary=f'{len(orders)} cancelled quotations in the selected scope.',
            model='sale.order',
            domain=[('state', '=', 'cancel')],
            record_ids=orders.ids,
            category='sales',
        )


@register_tool
class TopCustomersTool(BaseAITool):
    name = 'top_customers'
    description = 'Rank customers by confirmed sales revenue.'

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        limit = min(int(arguments.get('limit') or 10), 20)
        SaleOrder = self.env['sale.order']
        SaleOrder.check_access('read')
        groups = SaleOrder.read_group(
            [('state', 'in', ('sale', 'done'))],
            ['partner_id'],
            ['amount_total:sum'],
            limit=limit,
            order='amount_total:sum desc',
        )
        partner_ids = [partner_id for partner_id, __ in groups if partner_id]
        partner_names = {
            partner.id: partner.display_name
            for partner in self.env['res.partner'].sudo().browse(partner_ids)
        }
        lines = []
        for partner_id, amount_total in groups:
            if not partner_id:
                continue
            lines.append({
                'name': partner_names[partner_id],
                'revenue': amount_total,
            })
        return tool_result(
            headline=f'Top {len(lines)} customers',
            summary=f'Top customers by confirmed sales revenue.',
            model='res.partner',
            domain=[('id', 'in', partner_ids)],
            record_ids=partner_ids,
            lines=lines,
            category='sales',
        )


@register_tool
class BestSellingProductsTool(BaseAITool):
    name = 'best_selling_products'
    description = 'Rank products by sold quantity on confirmed sales lines.'

    def execute(self, arguments: dict[str, Any]) -> dict[str, Any]:
        limit = min(int(arguments.get('limit') or 10), 20)
        SaleLine = self.env['sale.order.line']
        SaleLine.check_access('read')
        groups = SaleLine.read_group(
            [('order_id.state', 'in', ('sale', 'done')), ('product_id', '!=', False)],
            ['product_id'],
            ['product_uom_qty:sum'],
            limit=limit,
            order='product_uom_qty:sum desc',
        )
        product_ids = [product_id for product_id, __ in groups if product_id]
        product_names = {
            product.id: product.display_name
            for product in self.env['product.product'].sudo().browse(product_ids)
        }
        lines = []
        for product_id, product_uom_qty in groups:
            if not product_id:
                continue
            lines.append({
                'name': product_names[product_id],
                'quantity': product_uom_qty,
            })
        return tool_result(
            headline=f'Top {len(lines)} products',
            summary='Best selling products by confirmed sales quantity.',
            model='product.product',
            domain=[('id', 'in', product_ids)],
            record_ids=product_ids,
            lines=lines,
            category='sales',
        )
