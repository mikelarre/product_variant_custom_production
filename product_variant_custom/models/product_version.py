# Copyright 2019 Mikel Arregi Etxaniz - AvanzOSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, exceptions, fields, models, _


class ProductVersion(models.Model):
    _name = "product.version"

    name = fields.Char(string="Name")
    product_tmpl_id = fields.Many2one(related="product_id.product_tmpl_id")
    product_id = fields.Many2one(comodel_name="product.product",
                                 string="Product")
    custom_value_ids = fields.One2many(comodel_name="product.version.line",
                                       inverse_name="product_version_id",
                                       string="Custom Values")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Customer")

    @api.multi
    def get_custom_value_lines(self):
        self.ensure_one()
        lines = []
        values = self.custom_value_ids
        for value in values:
            lines.append(
                (0, 0, {
                    'attribute_id': value.attribute_id.id,
                    'value_id': value.value_id.id,
                    'custom_value': value.custom_value,
                }))
        return lines


class ProductVersionLine(models.Model):
    _name = "product.version.line"

    product_version_id = fields.Many2one(comodel_name="product.version")
    attribute_id = fields.Many2one(comodel_name="product.attribute",
                                   string="Attribute")
    value_id = fields.Many2one(comodel_name="product.attribute.value",
                               string="Value")
    custom_value = fields.Char(string="Custom value")

    @api.constrains('custom_value')
    def _check_custom_range(self):
        for line in self:
            value = line.value_id
            try:
                custom = line.custom_value
                custom_value = float(custom)
            except ValueError:
                return
            if value.min_value == value.max_value == 0:
                return
            if custom_value < value.min_value >= 0:
                raise exceptions.UserError(_(
                    "Custom value is smaller than minimum allowed for this "
                    "value"))
            if custom_value > value.max_value >= 0:
                raise exceptions.UserError(_(
                    "Custom value is greater than maximum allowed for this "
                    "value"))


class VersionCustomLine(models.AbstractModel):
    _name = "version.custom.line"

    attribute_id = fields.Many2one(comodel_name="product.attribute",
                                   string="Attribute")
    value_id = fields.Many2one(comodel_name="product.attribute.value",
                               string="Value")
    custom_value = fields.Char(string="Custom value")

    @api.constrains('custom_value')
    def _check_custom_range(self):
        for line in self:
            value = line.value_id
            try:
                custom = line.custom_value
                custom_value = float(custom)
            except ValueError:
                return
            if value.min_value == value.max_value == 0:
                return
            if custom_value < value.min_value >= 0:
                raise exceptions.UserError(_(
                    "Custom value is smaller than minimum allowed for this "
                    "value"))
            if custom_value > value.max_value >= 0:
                raise exceptions.UserError(_(
                    "Custom value is greater than maximum allowed for this "
                    "value"))
