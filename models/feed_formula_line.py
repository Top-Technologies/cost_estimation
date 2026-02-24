
from odoo import models, fields, api

class FeedFormulaLine(models.Model):
    _name = 'feed.formula.line'
    _description = 'Feed Formula Line (components for a formula)'
    _order = 'sequence, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    formula_id = fields.Many2one('feed.formula', string='Formula', ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', default=10, tracking=True)
    type = fields.Selection([('raw','Raw Material'), ('pack','Packing Material'), ('fuel','Fuel')], string='Type', required=True, default='raw', tracking=True)
    name = fields.Char(string='Component Name', required=True, tracking=True)
    input_kg = fields.Float(string='Input', default=0.0, tracking=True)
    price_per_kg = fields.Float(string='Unit Price', default=0.0, tracking=True)
    total_cost = fields.Monetary(string='Total Cost', compute='_compute_total', store=True, currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', string='Currency', related='formula_id.company_id.currency_id', readonly=True)

    @api.depends('input_kg','price_per_kg')
    def _compute_total(self):
        for rec in self:
            rec.total_cost = (rec.input_kg or 0.0) * (rec.price_per_kg or 0.0)
            


