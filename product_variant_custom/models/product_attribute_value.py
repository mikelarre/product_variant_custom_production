# Copyright 2019 Mikel Arregi Etxaniz - AvanzOSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    min_value = fields.Float(string="Min Value")
    max_value = fields.Float(string="Max Value")
