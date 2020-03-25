# Copyright 2020 Mikel Arregi Etxaniz - AvanzOSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models, exceptions, _


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _action_create_mrp_dict(self):
        if not self.product_id:
            raise exceptions.Warning(_("select a product before create a "
                                       "manufaturing order"))
        if self.custom_value_lines and not self.product_version_id:
            raise exceptions.Warning(_("select a version before create a "
                                       "manufaturing order"))
        res = super()._action_mrp_dict()
        res['product_attribute_ids'] = \
            self.product_id._get_product_attributes_values_dict()
        res['custom_value_ids'] = self._set_custom_lines()
        return res
