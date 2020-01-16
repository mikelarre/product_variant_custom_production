# Copyright 2019 Mikel Arregi Etxaniz - AvanzOSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    product_version_id = fields.Many2one(comodel_name="product.version",
                                         name="Product Version",
                                         compute="_compute_product_version")

    @api.depends('product_id')
    def _compute_product_version(self):
        product_version = False
        try:
            product_version = self.sale_line_id.product_version_id.id
        except AttributeError:
            pass
        try:
            product_version = \
                product_version or self.purchase_line_id.product_version_id.id
        except AttributeError:
            pass
        try:
            product_version = product_version or \
                self.raw_material_production_id.product_version_id.id
        except AttributeError:
            pass
        self.product_version_id = product_version

