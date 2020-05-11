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

    product_tmpl_id = fields.Many2one(comodel_name="product.template")
    product_version_id = fields.Many2one(comodel_name="product.version",
                                         name="Product Version")
    product_attribute_ids = fields.One2many(
        comodel_name='sale.line.attribute', inverse_name='sale_line_id',
        string='Product attributes', copy=True, readonly=True,
        states={'draft': [('readonly', False)]},)
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
    _sql_constraints = [
        ('accountable_required_fields',
            "CHECK(display_type IS NOT NULL OR (product_uom IS NOT NULL))",
            "Missing required fields on accountable sale order line."),
    ]
    def _delete_product_attribute_ids(self):
        delete_values = []
        for value in self.product_attribute_ids:
            delete_values.append((2, value.id))
        return delete_values

    def _delete_custom_lines(self):
        delete_values = []
        for value in self.custom_value_ids:
            delete_values.append((2, value.id))
        return delete_values

    def _set_custom_lines(self):
        if self.product_version_id:
            return self.product_version_id.get_custom_value_lines()
        elif self.product_id:
            return self.product_id.get_custom_value_lines()


    @api.multi
    @api.onchange('product_tmpl_id')
    def onchange_product_template(self):
        self.ensure_one()
        self.product_attribute_ids = \
            self._delete_product_attribute_ids()
        self.custom_value_ids = self._delete_custom_lines()
        if self.product_tmpl_id:
            self.product_uom = self.product_tmpl_id.uom_id
            if (not self.product_tmpl_id.attribute_line_ids and
                    not self.product_id):
                self.product_id = (
                        self.product_tmpl_id.product_variant_ids and
                        self.product_tmpl_id.product_variant_ids[0])
                self.product_attribute_ids = (
                    self.product_id._get_product_attributes_values_dict())
            self.product_attribute_ids = (
                self.product_tmpl_id._get_product_attributes_dict())
            return {'domain': {'product_id':
                                   [('product_tmpl_id', '=',
                                     self.product_tmpl_id.id)]}}
        return {'domain': {}}

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = super().product_id_change()
        self.custom_value_ids = self._delete_custom_lines()
        self.product_attribute_ids = self._delete_product_attribute_ids()
        if self.product_id:
            product = self.product_id
            self.product_attribute_ids = \
                product._get_product_attributes_values_dict()

            self.custom_value_ids = self._set_custom_lines()
            version = self.product_id._find_version(self.custom_value_ids)
            self.product_version_id = version
        return result

    @api.onchange('product_attribute_ids')
    def onchange_product_attributes(self):
        product_obj = self.env['product.product']
        product_tmpl_id = self.product_tmpl_id
        self.product_id = product_obj._product_find(self.product_tmpl_id,
                                                    self.product_attribute_ids)
        self.product_tmpl_id = product_tmpl_id

    @api.onchange('product_version_id')
    def product_version_id_change(self):
        if self.product_version_id:
            self.product_id = self.product_version_id.product_id
        self.custom_value_ids = self._delete_custom_lines()
        self.custom_value_ids = self._set_custom_lines()


class SaleLineAttribute(models.Model):
    _inherit = "product.attribute.line"
    _name = 'sale.line.attribute'

    product_tmpl_id = fields.Many2one(related='sale_line_id.product_tmpl_id')
    sale_line_id = fields.Many2one(comodel_name='sale.order.line',
                                   string='Sale Order Line')


class SaleVersionCustomLine(models.Model):
    _inherit = "version.custom.line"
    _name = "sale.version.custom.line"

    line_id = fields.Many2one(comodel_name="sale.order.line")
