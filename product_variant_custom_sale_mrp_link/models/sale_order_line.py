# Copyright 2020 Mikel Arregi Etxaniz - AvanzOSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, exceptions, _


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _action_mrp_dict(self):
#        if not self.product_id:
#            raise exceptions.Warning(_("select a product before create a "
#                                       "manufaturing order"))
        # if self.custom_value_ids and not self.product_version_id:
        #     raise exceptions.Warning(_("select a version before create a "
        #                                "manufaturing order"))
        res = super()._action_mrp_dict()
        res['product_attribute_ids'] = [(0, 0, x) for x in
            self.product_id._get_product_attributes_values_dict()]
        res['custom_value_ids'] = self._set_custom_lines()
        return res

    @api.multi
    def button_copy_product_to_mrp(self):
        for sale_line in self:
            production_id = sale_line.mrp_production_id
            if production_id:
                production_id.product_tmpl_id = sale_line.product_tmpl_id
                production_id.product_id = sale_line.product_id
                sale_line.custom_value_ids.copy_to(production_id,
                                                   'custom_value_ids')
                sale_line.product_attribute_ids.copy_to(production_id,
                                                        'product_attribute_ids')

