# Copyright 2019 Mikel Arregi Etxaniz - AvanzOSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, _


class ProductProduct(models.Model):
    _inherit = "product.product"

    product_version_ids = fields.One2many(comodel_name='product.version',
                                          inverse_name='product_id')
    product_version_count = fields.Integer(string="Versions",
                                           compute="compute_product_versions")

    @api.depends('product_version_ids')
    def compute_product_versions(self):
        for product in self:
            product.product_version_count = len(product.product_version_ids)

    @api.multi
    def get_custom_value_lines(self):
        self.ensure_one()
        lines = []
        values = self.attribute_value_ids.filtered(
            lambda x: x.is_custom)
        for value in values:
            lines.append(
                (0, 0, {
                    'attribute_id': value.attribute_id.id,
                    'value_id': value.id,
                }))
        return lines

    @api.multi
    def get_custom_attributes(self):
        custom_attributes = []
        for product in self:
            for line in product.attribute_line_ids:
                if line.value_ids.filtered(lambda x: x.is_custom):
                    custom_attributes.append(line.attribute_id.id)
        return custom_attributes

    @api.model
    def _build_version_attributes_domain(self, version_id, custom_values):
        domain = []
        cont = 0
        assert len(self) == 1, _("Multiple products or none in _find_version "
                                 "method")
        domain.append(('product_version_id', '=', version_id.id))
        if len(custom_values) > 1:
            domain.extend(['|' for i in range(len(custom_values) - 1)])
        for custom_value in custom_values:
            if isinstance(custom_value, dict):
                value_id = custom_value.get('value_id')
            else:
                value_id = custom_value.value_id.id
            if value_id:
                domain.extend(['&', ('value_id', '=', value_id),
                              ('custom_value', '=',
                               custom_value.custom_value)])
                cont += 1
        return domain, cont

    @api.model
    def _find_version(self, custom_values):
        if self:
            versions = self.env['product.version'].search(
                [('product_id', '=', self.id)])
            version_line_obj = self.env['product.version.line']
            for version in versions:
                domain, cont = self._build_version_attributes_domain(
                    version, custom_values)
                custom_lines = version_line_obj.search(domain)
                if len(custom_lines) == cont:
                    return version
        return False

    def _all_attribute_lines_filled(self, attributes):
        for value in attributes:
            if not str(value.value_id):
                return False
        return True

    def get_product_dict(self, tmpl_id, attributes):
        values = attributes.mapped("value_id.id")
        return {
            'product_tmpl_id': tmpl_id.id,
            'attribute_value_ids': [(6, 0, values)],
            'active': tmpl_id.active,
        }

    def create_product_product(self, template=None, attributes=None):
        if template and attributes:
            product_id = self._product_find(template, attributes)
            if not product_id and self._all_attribute_lines_filled(attributes):
                product_dict = self.get_product_dict(template, attributes)
                return self.create(product_dict)


class ProductAttributeLine(models.AbstractModel):
    _name = 'product.attribute.line'

    product_tmpl_id = fields.Many2one(comodel_name="product.template")
    attribute_id = fields.Many2one(comodel_name='product.attribute',
                                string='Attribute')
    value_id = fields.Many2one(comodel_name='product.attribute.value',
                               domain="[('attribute_id', '=', attribute_id),"
                               "('id', 'in', possible_value_ids)]",
                               string='Value')
    possible_value_ids = fields.Many2many(
        comodel_name='product.attribute.value',
        compute='_get_possible_attribute_values')

    def _get_possible_values(self):
        attr_values = self.env['product.attribute.value']
        template = self.product_tmpl_id
        for attr_line in template.attribute_line_ids:
            if attr_line.attribute_id.id == \
                    self.attribute_id.id:
                attr_values |= attr_line.value_ids
        return attr_values.sorted()

    @api.depends('attribute_id', 'product_tmpl_id',
                 'product_tmpl_id.attribute_line_ids')
    def _get_possible_attribute_values(self):
        for attribute_value in self:
            attribute_value.possible_value_ids = \
                attribute_value._get_possible_values()

    @api.multi
    def copy_to(self, instance, field):
        for line in instance[field]:
            line.unlink()
        copy_fields = []
        for attribute_line in self:
            copy_fields.append((0, 0, {
                'attribute_id': attribute_line.attribute_id,
                'value_id': attribute_line.value_id,
                'possible_value_ids': attribute_line.possible_value_ids,
            }))
        instance[field] = copy_fields