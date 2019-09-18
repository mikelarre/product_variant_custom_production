# Copyright 2019 Mikel Arregi Etxaniz - AvanzOSC
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.multi
    def _action_confirm(self):
        res = super()._action_confirm()
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
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    product_version_id = fields.Many2one(comodel_name="product.version",
                                         name="Product Version")
    version_value_ids = fields.One2many(
        comodel_name="product.version.line",
        related="product_version_id.custom_value_ids")
    custom_value_ids = fields.One2many(
        comodel_name="sale.version.custom.line", string="Custom Values",
        inverse_name="line_id", copy=True)
    # possible_attribute_ids = fields.Many2many(
    #     comodel_name="product.attribute",
    #     compute="_compute_possible_attribute_ids")
    #
    # @api.depends("product_id")
    # def _compute_possible_attribute_ids(self):
    #     for line in self:
    #         attribute_ids = line.product_id.get_custom_attributes()
    #         line.possible_attribute_ids = [(6, 0, attribute_ids)]

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
    def product_id_change(self):
        res = super().product_id_change()
        self.custom_value_ids = self._set_custom_lines()
        self.product_version_id = False
        return res

    @api.onchange('product_version_id')
    def product_version_id_change(self):
        if self.product_version_id:
            self.product_id = self.product_version_id.product_id
        else:
            self.custom_value_ids = self._set_custom_lines()


class SaleVersionCustomLine(models.Model):
    _inherit = "version.custom.line"
    _name = "sale.version.custom.line"

    line_id = fields.Many2one(comodel_name="sale.order.line")
