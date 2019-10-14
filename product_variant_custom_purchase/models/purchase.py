# Copyright 2019 Mikel Arregi Etxaniz - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.multi
    def button_approve(self, force=False):
        for line in self.order_line:
            product_version = line.product_id._find_version(
                line.custom_value_ids)
            if product_version:
                line.product_version_id = product_version
            else:
                custom_value_ids = []
                name = ""
                for custom in line.custom_value_ids:
                    if custom.custom_value:
                        custom_value_ids.append((0, 0, {
                            'attribute_id': custom.attribute_id.id,
                            'value_id': custom.value_id.id,
                            'custom_value': custom.custom_value,
                        }))
                        if name:
                            name = "{}, ({}):{}".format(
                                name, custom.value_id.name, custom.custom_value
                            )
                        else:
                            name = "({}):{}".format(
                                custom.value_id.name, custom.custom_value)
                product_version = self.env["product.version"].create({
                    'product_id': line.product_id.id,
                    'name': name,
                    'custom_value_ids': custom_value_ids,
                })
                line.product_version_id = product_version
        return super().button_approve()


class PurchaseOrder(models.Model):
    _inherit = "purchase.order.line"

    product_version_id = fields.Many2one(comodel_name="product.version",
                                         name="Product Version")
    version_value_ids = fields.One2many(
        comodel_name="product.version.line",
        related="product_version_id.custom_value_ids")
    custom_value_ids = fields.One2many(
        comodel_name="purchase.version.custom.line", string="Custom Values",
        inverse_name="line_id", copy=True)

    def _set_custom_lines(self):
        for value in self.custom_value_ids:
            self.custom_value_ids = [(2, value)]
        lines = []
        values = self.product_id.attribute_value_ids.filtered(
            lambda x: x.is_custom)
        for value in values:
            lines.append(
                (0, 0, {
                    'attribute_id': value.attribute_id.id,
                    'value_id': value.id,
                }))
        return lines

    @api.onchange('product_id')
    def onchange_product_id(self):
        res = super().onchange_product_id()
        self.custom_value_ids = self._set_custom_lines()
        self.product_version_id = False
        return res

    @api.onchange('product_version_id')
    def product_version_id_change(self):
        if self.product_version_id:
            self.product_id = self.product_version_id.product_id
        else:
            self.custom_value_ids = self._set_custom_lines()


class PurchaseVersionCustomLine(models.Model):
    _inherit = "version.custom.line"
    _name = "purchase.version.custom.line"

    line_id = fields.Many2one(comodel_name="purchase.order.line")
