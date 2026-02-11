from odoo import models, fields

class FeedFormula(models.Model):
    _name = 'feed.formula'
    _description = 'Feed Formula'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, tracking=True)
    code = fields.Char(tracking=True)
    description = fields.Text(tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    # BOM-like component lines
    line_ids = fields.One2many('feed.formula.line', 'formula_id', string='Components', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, tracking=True)
    