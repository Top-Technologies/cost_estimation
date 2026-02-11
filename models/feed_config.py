from odoo import models, fields, api


class FeedConfig(models.Model):
    _name = 'feed.config'
    _description = 'Feed Estimation Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(string='Configuration Name(machine)', required=True,
                       copy=False, default='New', tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True,tracking=True,
                                 default=lambda self: self.env.company)
    daily_produced_q = fields.Float(
        string='Daily Produced (Quintal)',tracking=True, default=170.0)
    annual_working_days = fields.Integer(
        string='Annual Working Days',tracking=True, default=313)
    monthly_working_days = fields.Integer(
        string='Monthly Working Days',tracking=True, default=26)
    machine_price_config = fields.Integer(string='machine price', tracking=True, default=0)
    depreciation_percent = fields.Float(
        string='Depreciation Percent', default=20.0, tracking=True)
    interest_rate_percent = fields.Float(
        string='Interest Rate (annual %)', default=0.0, tracking=True)
    allow_config_edit_group_id = fields.Many2one(
        'res.groups', string='Group who can edit', tracking=True)
    _sql_constraints = [
        ('company_uniq', 'unique(company_id)',
         'Configuration for this company already exists.'),
    ]

    @api.model
    def get_config(self):
        config = self.search(
            [('company_id', '=', self.env.company.id)], limit=1)
        if not config:
            config = self.create({'company_id': self.env.company.id})
        return config
