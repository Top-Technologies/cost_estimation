from odoo import models, fields, api


class FeedConfig(models.Model):
    _name = 'feed.config'
    _description = 'Feed Estimation Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    name = fields.Char(string='Configuration Name(machine)', required=True,
                       copy=False, default='New', tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True,tracking=True,
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency', 
                              default=lambda self: self.env.company.currency_id)

    daily_produced_q = fields.Float(
        string='Daily Produced',tracking=True, default=170.0)
    annual_working_days = fields.Integer(
        string='Annual Working Days',tracking=True, default=313)
    monthly_working_days = fields.Integer(
        string='Monthly Working Days',tracking=True, default=26)
    labor_salary_monthly_config = fields.Monetary(
        string='Total Monthly Labor Salary', currency_field='currency_id')
    machine_price_config = fields.Integer(string='Machine Price', tracking=True, default=0)
    loan_amount_config = fields.Monetary(
        string='Loan Amount (Machinery)', currency_field='currency_id')
    depreciation_percent = fields.Float(
        string='Depreciation Percent', default=20.0, tracking=True)
    interest_rate_percent = fields.Float(
        string='Interest Rate (annual %)', default=0.0, tracking=True)
    last_10m_rm_total_config = fields.Monetary(
        string='Last 10-month Repair & Maintenance Total', currency_field='currency_id')
    loading_cost_per_quintal_input_config = fields.Monetary(
        string='Loading Cost / Q (input)', currency_field='currency_id', help='User-provided loading cost per quintal (currency per Q)')
    allow_config_edit_group_id = fields.Many2one(
        'res.groups', string='Group who can edit', tracking=True)
    is_default = fields.Boolean(string='Default')
    # _sql_constraints = [
    #     ('company_uniq', 'unique(company_id)',
    #      'Configuration for this company already exists.'),
    # ]

    @api.model
    def get_config(self, company):
        """
        Get feed configuration for given company.
        Auto-create if not exists.
        """

        if not company:
            company = self.env.company

        config = self.search(
            [('company_id', '=', company.id)],
            limit=1
        )

        if not config:
            config = self.create({
                'company_id': company.id,
                'name': company.name + ' Configuration'
            })

        return config
