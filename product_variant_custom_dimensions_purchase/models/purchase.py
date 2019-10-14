# Copyright 2019 Mikel Arregi Etxaniz - AvanzOSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    dimension = fields.Float(string="Product Dimension",
                             related="product_id.dimension")
    weight = fields.Float(string="Product Weight",
                          related="product_id.product_base_weight")
    version_dimension = fields.Float(string="Product Dimension",
                                     related="product_version_id.dimension")
    version_weight = fields.Float(
        string="Product Weight",
        related="product_version_id.product_base_weight")
    total_dimension = fields.Float(string="Total Dimension",
                                   compute="_compute_total_dimension_weight")
    total_weight = fields.Float(string="Total Weight",
                                compute="_compute_total_dimension_weight")
    invisible_dimension = fields.Boolean(string="Invisible Dimension",
        related="product_id.invisible_dimension")

    @api.depends("product_id", "product_version_id", "product_qty")
    def _compute_total_dimension_weight(self):
        for line in self:
            if line.product_version_id:
                dimension = line.version_dimension
                weight = line.version_weight
            else:
                dimension = line.dimension
                weight = line.weight
            line.total_dimension = dimension * line.product_qty
            line.total_weight = weight * line.product_qty

    @api.depends('product_qty', 'price_unit', 'taxes_id')
    def _compute_amount(self):
        super()._compute_amount()
        for line in self:
            price_by = line.product_id.product_tmpl_id.price_by
            if price_by == 'qty':
                continue
            if price_by == 'dimension':
                if line.product_version_id:
                    dimension = line.version_dimension
                else:
                    dimension = line.dimension
                line.update({
                    'price_tax': line['price_tax'] * dimension,
                    'price_total': line['price_total'] * dimension,
                    'price_subtotal': line['price_subtotal'] * dimension,
                })
            else:
                if line.product_version_id:
                    weight = line.version_weight
                else:
                    weight = line.weight
                line.update({
                    'price_tax': line['price_tax'] * weight,
                    'price_total': line['price_total'] * weight,
                    'price_subtotal': line['price_subtotal'] * weight,
                })
