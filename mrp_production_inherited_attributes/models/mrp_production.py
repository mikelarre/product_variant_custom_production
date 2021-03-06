# Copyright 2019 Mikel Arregi Etxaniz - AvanzOSC
# Copyright 2019 Oihane Crucelaegui - AvanzOSC
# Copyright 2019 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models, fields, api, exceptions, _


class MrpProductionAttribute(models.Model):
    _name = 'mrp.production.attribute'

    mrp_production = fields.Many2one(comodel_name='mrp.production',
                                     string='Manufacturing Order')
    attribute_id = fields.Many2one(comodel_name='product.attribute',
                                string='Attribute')
    value_id = fields.Many2one(comodel_name='product.attribute.value',
                               domain="[('attribute_id', '=', attribute_id),"
                               "('id', 'in', possible_value_ids)]",
                               string='Value')
    possible_value_ids = fields.Many2many(
        comodel_name='product.attribute.value',
        compute='_get_possible_attribute_values')

    @api.depends('attribute_id', 'mrp_production.product_tmpl_id',
                 'mrp_production.product_tmpl_id.attribute_line_ids')
    def _get_possible_attribute_values(self):
        for attribute_value in self:
            attr_values = attribute_value.env['product.attribute.value']
            template = attribute_value.mrp_production.product_tmpl_id
            for attr_line in template.attribute_line_ids:
                if attr_line.attribute_id.id == \
                        attribute_value.attribute_id.id:
                    attr_values |= attr_line.value_ids
            attribute_value.possible_value_ids = attr_values.sorted()


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    product_id = fields.Many2one(required=False)
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template', string='Product', readonly=True,
        states={'draft': [('readonly', False)]})
    product_attribute_ids = fields.One2many(
        comodel_name='mrp.production.attribute', inverse_name='mrp_production',
        string='Product attributes', copy=True, readonly=True,
        states={'draft': [('readonly', False)]},)

    @api.onchange('product_id')
    def onchange_product_id(self):
        result = super().onchange_product_id()
        if self.product_id:
            bom_obj = self.env['mrp.bom']
            product = self.product_id
            if not self.bom_id:
                self.bom_id = bom_obj._bom_find(
                    product_tmpl=product.product_tmpl_id)
            self.product_attribute_ids = \
                product._get_product_attributes_values_dict()
            self.routing_id = self.bom_id.routing_id.id or False
        return result

    @api.multi
    def _onchange_bom_id(self):
        res = super(MrpProduction, self)._onchange_bom_id()
        if self.bom_id:
            bom = self.bom_id
            if bom.product_id:
                self.product_id = bom.product_id.id
            else:
                self.product_tmpl_id = bom.product_tmpl_id.id
            if 'domain' not in res:
                res['domain'] = {}
            res['domain']['routing_id'] = [('id', '=', bom.routing_id.id)]
        return res

    @api.multi
    @api.onchange('product_tmpl_id')
    def onchange_product_template(self):
        self.ensure_one()
        if self.product_tmpl_id:
            self.product_uom = self.product_tmpl_id.uom_id
            if (not self.product_tmpl_id.attribute_line_ids and
                    not self.product_id):
                self.product_id = (
                    self.product_tmpl_id.product_variant_ids and
                    self.product_tmpl_id.product_variant_ids[0])
            if not self.product_id:
                self.product_attribute_ids = (
                    self.product_tmpl_id._get_product_attributes_dict())
            else:
                self.product_attribute_ids = (
                    self.product_id._get_product_attributes_values_dict())
            self.bom_id = self.env['mrp.bom']._bom_find(
                product_tmpl=self.product_tmpl_id)
            self.routing_id = self.bom_id.routing_id
            return {'domain': {'product_id':
                               [('product_tmpl_id', '=',
                                 self.product_tmpl_id.id)],
                               'bom_id':
                               [('product_tmpl_id', '=',
                                 self.product_tmpl_id.id)]}}
        return {'domain': {}}

    @api.onchange('product_attribute_ids')
    def onchange_product_attributes(self):
        product_obj = self.env['product.product']
        product_tmpl_id = self.product_tmpl_id
        self.product_id = product_obj._product_find(self.product_tmpl_id,
                                                    self.product_attribute_ids)
        self.product_tmpl_id = product_tmpl_id

    @api.multi
    def _action_compute_lines(self):
        results = self._action_compute_lines_variants()
        return results

    @api.multi
    def _action_compute_lines_variants(self):
        """ Compute product_lines and workcenter_lines from BoM structure
        @return: product_lines
        """
        results = []
        bom_obj = self.env['mrp.bom']
        product_obj = self.env['product.product']
        prod_line_obj = self.env['mrp.production.product.line']

        # workcenter_line_obj = self.env['mrp.production.workcenter.line']
        for production in self:
            uom_id = self.env['uom.uom'].browse(production.product_uom_id.id)
            #  unlink product_lines
            production.product_line_ids.unlink()
            #  unlink workcenter_lines
            # production.workcenter_lines.unlink()
            #  search BoM structure and route
            bom_id = production.bom_id
            if not bom_id:
                if not production.product_id:
                    bom_id = bom_obj._bom_find(
                        product_tmpl=production.product_tmpl_id)
                else:
                    bom_id = bom_obj._bom_find(
                        product=production.product_id)
                if bom_id:
                    routing_id = bom_id.routing_id or False
                    self.write({'bom_id': bom_id.id,
                                'routing_id': routing_id.id})
            if not bom_id:
                raise exceptions.Warning(
                    _('Error! Cannot find a bill of material for this'
                      ' product.'))

            # get components and workcenter_lines from BoM structure
            factor = uom_id._compute_quantity(production.product_qty,
                                              bom_id.product_uom_id)
            # product_lines, workcenter_lines
            results, results2 = bom_id.explode(production.product_id,
                factor / bom_id.product_qty)

            #  reset product_lines in production order
            for done_line, line in results2:
                product_id = done_line.product_id or \
                             product_obj._product_find(
                                 done_line.product_tmpl_id,
                                 list(map(lambda x: x[2],
                                          line['product_attribute_ids']))) \
                             or product_obj
                product_tmpl_id = done_line.product_tmpl_id
                production_product_line = {
                    'name': product_id.name or done_line.product_tmpl_id.name,
                    'production_id': production.id,
                    'bom_line_id': done_line.id,
                    'product_attribute_ids': line['product_attribute_ids'],
                    'product_tmpl_id': product_tmpl_id.id,
                    'product_id': product_id.id,
                    'product_qty': line['qty'],
                    'product_uom_id': done_line.product_uom_id.id,
                }
                prod_line_obj.create(production_product_line)

            #  reset workcenter_lines in production order
            # for line in results2:
            #     line['production_id'] = production.id
            #     workcenter_line_obj.create(line)
        return results

    @api.multi
    def _check_create_production_product(self):
        if not self.product_tmpl_id and not self.product_id:
            raise exceptions.Warning(
                _("You can not confirm without product or variant defined."))
        if not self.product_id:
            product_obj = self.env['product.product']
            att_values_ids = [
                attr_line.value and attr_line.value.id or False
                for attr_line in self.product_attribute_ids]
            domain = [('product_tmpl_id', '=', self.product_tmpl_id.id)]
            for value in att_values_ids:
                if not value:
                    raise exceptions.Warning(
                        _("You can not confirm before configuring all"
                          " attribute values."))
                domain.append(('attribute_value_ids', '=', value))
            product = product_obj.search(domain)
            if not product:
                product = product_obj.create(
                    {'product_tmpl_id': self.product_tmpl_id.id,
                     'attribute_value_ids': [(6, 0, att_values_ids)]})
            self.product_id = product

    @api.multi
    def _check_create_scheduled_product_lines_product(self, line):
        if not line.product_id:
            product_obj = self.env['product.product']
            att_values_ids = [attr_line.value_id.id or False
                              for attr_line in line.product_attribute_ids]
            domain = [('product_tmpl_id', '=', line.product_tmpl_id.id)]
            for value in att_values_ids:
                if not value:
                    raise exceptions.Warning(
                        _("You can not confirm before configuring all"
                          " attribute values."))
                domain.append(('attribute_value_ids', '=', value))
            product = product_obj.search(domain)
            if not product:
                product = product_obj.create(
                    {'product_tmpl_id': line.product_tmpl_id.id,
                     'attribute_value_ids': [(6, 0, att_values_ids)]})
            line.product_id = product
        return True

    @api.multi
    def button_confirm(self):
        self._check_create_production_product()
        for line in self.product_line_ids:
            if not self._check_create_scheduled_product_lines_product(line):
                raise exceptions.UserError(_("Scheduled lines checking error"))
        return super(MrpProduction,
                     self).button_confirm()


class MrpProductionProductLineAttribute(models.Model):
    _name = 'mrp.production.product.line.attribute'

    product_line = fields.Many2one(
        comodel_name='mrp.production.product.line',
        string='Product line')
    attribute_id = fields.Many2one(comodel_name='product.attribute',
                                string='Attribute')
    value_id = fields.Many2one(comodel_name='product.attribute.value',
                            domain="[('attribute_id', '=', attribute_id),"
                            "('id', 'in', possible_value_ids)]",
                            string='Value')
    possible_value_ids = fields.Many2many(
        comodel_name='product.attribute.value',
        compute='_get_possible_attribute_values')

    @api.one
    def _get_parent_value(self):
        if self.attribute_id.parent_inherited:
            production = self.product_line.production_id
            for attr_line in production.product_attribute_ids:
                if attr_line.attribute_id == self.attribute_id:
                    self.value_id = attr_line.value_id

    @api.one
    @api.depends('attribute_id')
    def _get_possible_attribute_values(self):
        attr_values = self.env['product.attribute.value']
        template = self.product_line.product_tmpl_id
        for attr_line in template.attribute_line_ids:
            if attr_line.attribute_id.id == self.attribute_id.id:
                attr_values |= attr_line.value_ids
        self.possible_value_ids = attr_values.sorted()


class MrpProductionProductLine(models.Model):
    _inherit = 'mrp.production.product.line'

    product_id = fields.Many2one(required=False)
    product_tmpl_id = fields.Many2one(comodel_name='product.template',
                                       string='Product')
    product_attribute_ids = fields.One2many(
        comodel_name='mrp.production.product.line.attribute',
        inverse_name='product_line', string='Product attributes',
        copy=True)

    @api.onchange('product_tmpl_id')
    def onchange_product_template(self):
        if self.product_tmpl_id:
            product_id = self.env['product.product']
            if not self.product_tmpl_id.attribute_line_ids:
                product_id = (self.product_tmpl_id.product_variant_ids and
                              self.product_tmpl_id.product_variant_ids[0])
                product_attributes = (
                    product_id._get_product_attributes_values_dict())
            else:
                product_attributes = (
                    self.product_tmpl_id._get_product_attributes_inherit_dict(
                        self.production_id.product_attributes))
            self.name = product_id.name or self.product_tmpl_id.name
            self.product_uom = self.product_tmpl_id.uom_id
            self.product_id = product_id
            self.product_attribute_ids = product_attributes

    @api.onchange('product_attribute_ids')
    def onchange_product_attributes(self):
        product_obj = self.env['product.product']
        self.product_id = product_obj._product_find(
            self.product_tmpl_id, self.product_attribute_ids)
