# Copyright 2019 Mikel Arregi Etxaniz - AvanzOSC
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, fields, models
from odoo.tools.float_utils import float_round


class StockMove(models.Model):
    _inherit = "stock.move"

    product_version_id = fields.Many2one(comodel_name="product.version",
                                         name="Product Version",
                                         compute="_compute_product_version",
                                         store="True")
    real_in = fields.Float(string="Real In",
                           compute="_compute_move_in_out_qty", store="True")
    real_out = fields.Float(string="Real Out",
                            compute="_compute_move_in_out_qty", store="True")
    virtual_in = fields.Float(string="Virtual In",
                              compute="_compute_move_in_out_qty", store="True")
    virtual_out = fields.Float(string="Virtual Out",
                               compute="_compute_move_in_out_qty",
                               store="True")

    def _calculate_qty_available(self, domain_move_in_loc, domain_move_out_loc):
        domain_move_in = [('product_id', 'in', self.ids)] + domain_move_in_loc
        domain_move_out = [('product_id', 'in', self.ids)] + domain_move_out_loc
        domain_move_in_todo = [('state', '=', 'done')] + domain_move_in
        domain_move_out_todo = [('state', '=', 'done')] + domain_move_out
        Move = self.env['stock.move']
        moves_in_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        moves_res = dict(
            (item['product_id'][0],
             moves_in_res[item['product_id'][0]] - item['product_qty'])
            for item in Move.read_group(
                domain_move_out_todo, ['product_id', 'product_qty'],
                ['product_id'], orderby='id'))
        return moves_res

    @api.depends("location_id", "location_dest_id", "product_qty")
    def _compute_move_in_out_qty(self):
        for move in moves:
            self.env['product.product']._get_domain_locations_new(move)
        domain_quant_loc, domain_move_in_loc, domain_move_out_loc = self._get_domain_locations()
        domain_move_in = [('product_id', 'in', self.ids)] + domain_move_in_loc
        domain_move_out = [('product_id', 'in', self.ids)] + domain_move_out_loc
        domain_move_in_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_in
        domain_move_out_todo = [('state', 'in', ('waiting', 'confirmed', 'assigned', 'partially_available'))] + domain_move_out
        Move = self.env['stock.move']
        moves_in_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_in_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        moves_out_res = dict((item['product_id'][0], item['product_qty']) for item in Move.read_group(domain_move_out_todo, ['product_id', 'product_qty'], ['product_id'], orderby='id'))
        res = dict()
        qty_available = self._calculate_qty_available(domain_move_in_loc,
                                                  domain_move_out_loc)
        for product in self.with_context(prefetch_fields=False):
            product_id = product.id
            rounding = product.uom_id.rounding
            qty_available = self._calculate_qty_available(product)
            res[product_id] = {}
            res[product_id]['qty_available'] = float_round(qty_available, precision_rounding=rounding)
            res[product_id]['incoming_qty'] = float_round(moves_in_res.get(product_id, 0.0), precision_rounding=rounding)
            res[product_id]['outgoing_qty'] = float_round(moves_out_res.get(product_id, 0.0), precision_rounding=rounding)
            res[product_id]['virtual_available'] = float_round(
                qty_available + res[product_id]['incoming_qty'] - res[product_id]['outgoing_qty'],
                precision_rounding=rounding)
        for product in self.with_context(prefetch_fields=False):
            product_id = product.id
            rounding = product.uom_id.rounding
            res[product_id] = {}
            res[product_id]['qty_available'] = float_round(qty_available, precision_rounding=rounding)
            res[product_id]['incoming_qty'] = float_round(moves_in_res.get(product_id, 0.0), precision_rounding=rounding)
            res[product_id]['outgoing_qty'] = float_round(moves_out_res.get(product_id, 0.0), precision_rounding=rounding)
            res[product_id]['virtual_available'] = float_round(
                qty_available + res[product_id]['incoming_qty'] - res[product_id]['outgoing_qty'],
                precision_rounding=rounding)
        for move in self:
            if move.state not in ["draft", "cancel"]:
                if move.location_id.usage == "internal" and \
                        move.location_dest_id == "customer":
                    move.real_out = move.product_qty - move.remaining_qty
                    move.virtual_out = move.product_qty
                if move.location_id.usage == "customer" and \
                        move.location_dest_id == "supplier":
                    move.real_in = move.product_qty - move.remaining_qty
                    move.virtual_in = move.product_qty


    @api.depends('product_id')
    def _compute_product_version(self):
        for move in self:
            product_version = False
            try:
                product_version = move.sale_line_id.product_version_id
            except AttributeError:
                pass
            try:
                product_version = \
                    product_version or \
                    move.purchase_line_id.product_version_id
            except AttributeError:
                pass
            try:
                product_version = product_version or \
                    move.raw_material_production_id.product_version_id
            except AttributeError:
                pass
            move.product_version_id = product_version



