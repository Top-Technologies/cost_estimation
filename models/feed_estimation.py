from odoo import models, fields, api
from odoo.exceptions import UserError



class FeedEstimation(models.Model):
    _name = 'feed.estimation'
    _description = 'Feed Cost Estimation'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True,
                       copy=False, default='New')
    formula_id = fields.Many2one(
        'feed.formula', string='Formula', required=True)
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    date = fields.Date(default=fields.Date.context_today)
    state = fields.Selection(
        [('draft', 'Draft'), ('computed', 'Computed')], default='draft')

    # configurable but copied from config on create
    total_quintal_daily = fields.Float(
        string='Daily Produced (Quintal)', default=170.0)
    annual_working_days = fields.Integer(
        string='Annual Working Days', default=313)
    monthly_working_days = fields.Integer(
        string='Monthly Working Days', default=26)

    labor_salary_monthly = fields.Monetary(
        string='Total Monthly Labor Salary', currency_field='currency_id')
    machine_price = fields.Monetary(
        string='Machine Price', currency_field='currency_id')
    loan_amount = fields.Monetary(
        string='Loan Amount (Machinery)', currency_field='currency_id')
    interest_rate = fields.Float(
        string='Interest Rate (annual %)', default=0.0)
    last_10m_rm_total = fields.Monetary(
        string='Last 10-month Repair & Maintenance Total', currency_field='currency_id')

    # Loading cost input (per quintal) - user gives loading cost per Q (currency/Q)
    loading_cost_per_quintal_input = fields.Monetary(
        string='Loading Cost / Q (input)', currency_field='currency_id', help='User-provided loading cost per quintal (currency per Q)')

    # computed fields for loading
    monthly_loading_cost = fields.Monetary(
        string='Monthly Loading Cost', compute='_compute_totals', store=True, currency_field='currency_id')
    daily_loading_cost = fields.Monetary(
        string='Daily Loading Cost', compute='_compute_totals', store=True, currency_field='currency_id')

    line_ids = fields.One2many(
        'feed.estimation.line', 'estimation_id', string='Materials')
    
    # fuel total
    fuel_total = fields.Monetary(string='Fuel Total', compute='_compute_totals', store=True, currency_field='currency_id')

    # Computed totals
    raw_material_total = fields.Monetary(
        string='Raw Material Total', compute='_compute_totals', store=True, currency_field='currency_id')
    packing_material_total = fields.Monetary(
        string='Packing Material Total', compute='_compute_totals', store=True, currency_field='currency_id')
    labor_cost_per_quintal = fields.Float(
        string='Labor Cost / Quintal', compute='_compute_totals', store=True)
    depreciation_per_quintal = fields.Float(
        string='Depreciation / Quintal', compute='_compute_totals', store=True)
    interest_per_quintal = fields.Float(
        string='Interest / Quintal', compute='_compute_totals', store=True)
    other_cost_per_quintal = fields.Float(
        string='Other Cost / Quintal', compute='_compute_totals', store=True)
    loading_cost_per_quintal = fields.Float(
        string='Loading Cost / Quintal', compute='_compute_totals', store=True)
    total_cost_per_quintal = fields.Float(
        string='Total Cost / Quintal', compute='_compute_totals', store=True)

    def _get_annual_produced_quintal(self, rec):
        return (rec.total_quintal_daily or 0.0) * (rec.annual_working_days or 1)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            # copy defaults from config
            config = self.env['feed.config'].get_config()
            rec.total_quintal_daily = rec.total_quintal_daily or config.daily_produced_q
            rec.annual_working_days = rec.annual_working_days or config.annual_working_days
            rec.monthly_working_days = rec.monthly_working_days or config.monthly_working_days
            rec.interest_rate = rec.interest_rate or config.interest_rate_percent
            rec.machine_price = rec.machine_price or config.machine_price_config
            if rec.name == 'New':
                rec.name = self.env['ir.sequence'].sudo().next_by_code(
                    'feed.estimation') or 'FEST/' + fields.Date.today().strftime('%Y%m%d')
            # If formula has components and estimation has no manual lines, populate lines from formula (copy)
            if rec.formula_id and not rec.line_ids:
                lines_to_create = []
                for fl in rec.formula_id.line_ids:
                    lines_to_create.append((0, 0, {
                        'type': fl.type,
                        'name': fl.name,
                        'input_kg': fl.input_kg,
                        'price_per_kg': fl.price_per_kg,
                    }))
                if lines_to_create:
                    rec.line_ids = lines_to_create
        return records
    
    
    @api.onchange('formula_id')
    def _onchange_formula(self):
        """When user selects a formula in the Estimation form, prefill lines from formula.
           This is client-side and won't persist unless the user saves the record."""
        for rec in self:
            if rec.formula_id:
                lines_to_set = []
                for fl in rec.formula_id.line_ids:
                    lines_to_set.append((0, 0, {
                        'type': fl.type,
                        'name': fl.name,
                        'input_kg': fl.input_kg,
                        'price_per_kg': fl.price_per_kg,
                    }))
                rec.line_ids = lines_to_set



    @api.onchange('formula_id')
    def _onchange_load_config(self):
        config = self.env['feed.config'].get_config()

        self.total_quintal_daily = config.daily_produced_q
        self.annual_working_days = config.annual_working_days
        self.monthly_working_days = config.monthly_working_days
        self.interest_rate = config.interest_rate_percent
        self.machine_price = config.machine_price_config

    @api.depends('line_ids.total_cost', 'labor_salary_monthly', 'machine_price', 'loan_amount', 'interest_rate', 'last_10m_rm_total', 'total_quintal_daily', 'annual_working_days', 'monthly_working_days', 'loading_cost_per_quintal_input')
    def _compute_totals(self):
        for rec in self:
            # Sum lines
            raw_total = sum(
                l.total_cost for l in rec.line_ids if l.type == 'raw')
            pack_total = sum(
                l.total_cost for l in rec.line_ids if l.type == 'pack')
            fuel_total = sum(l.total_cost for l in rec.line_ids if l.type == 'fuel')

            # Apply 2% waste adjustment to raw materials (raw_total_adjusted = raw_total / 0.98)
            # Guard division by zero (0.98 is constant > 0)
            raw_total_adjusted = (raw_total or 0.0) / 0.98

            # Store original totals (unadjusted) for reporting, and store adjusted raw as raw_material_total
            rec.raw_material_total = raw_total_adjusted
            rec.packing_material_total = pack_total
            rec.fuel_total = fuel_total

            # Labor
            monthly_days = rec.monthly_working_days or 1
            daily_labor = (rec.labor_salary_monthly or 0.0) / (monthly_days)
            labor_per_q = (daily_labor / (rec.total_quintal_daily or 1.0)
                           ) if rec.total_quintal_daily else 0.0
            rec.labor_cost_per_quintal = labor_per_q

            # Depreciation
            config = self.env['feed.config'].get_config()
            dep_percent = (config.depreciation_percent or 20.0) / 100.0
            total_depr_amount = (rec.machine_price or 0.0) * dep_percent
            annual_produced_q = self._get_annual_produced_quintal(rec) or 1.0
            depr_per_q = (total_depr_amount / annual_produced_q)
            rec.depreciation_per_quintal = depr_per_q

            # Interest
            interest_per_year = (rec.loan_amount or 0.0) * \
                ((rec.interest_rate or 0.0) / 100.0)
            yearly_days = 313
            daily_interest = interest_per_year / (yearly_days)
            interest_per_q = daily_interest / (rec.total_quintal_daily or 1.0)
            rec.interest_per_quintal = interest_per_q

            # Other costs (repair & maintenance last 10 months)
            monthly_other = (rec.last_10m_rm_total or 0.0) / 10.0
            other_per_day = (monthly_other / (rec.monthly_working_days or 1))
            other_per_q = other_per_day / (rec.total_quintal_daily or 1.0)
            rec.other_cost_per_quintal = other_per_q

            # Loading cost calculations (per your formulas)
            # Monthly produced quintal (for the month) = daily_q * monthly_working_days
            monthly_produced_q = (
                rec.total_quintal_daily or 0.0) * (rec.monthly_working_days or 1)
            monthly_loading = monthly_produced_q * \
                (rec.loading_cost_per_quintal_input or 0.0)
            daily_loading = monthly_loading / (rec.monthly_working_days or 1)
            loading_per_q = (daily_loading / (rec.total_quintal_daily or 1.0)
                             ) if rec.total_quintal_daily else 0.0

            rec.monthly_loading_cost = monthly_loading
            rec.daily_loading_cost = daily_loading
            rec.loading_cost_per_quintal = loading_per_q

            # Loading cost will be included in total per quintal

            # Combine RM (adjusted) + Packing + Fuel into per-quintal basis.
            # NOTE: raw_total_adjusted, pack_total and fuel_total are totals (currency) for the batch/month as entered.
            # The Excel logic originally divided raw+pack by annual produced quintal to get per-Q; here we do same with annual produced Q.
            annual_produced_q = self._get_annual_produced_quintal(rec) or 1.0
            rm_pack_fuel_total_adjusted = (raw_total_adjusted + pack_total + fuel_total)
            rm_pack_fuel_per_q = (rm_pack_fuel_total_adjusted)

            total_per_q = (rm_pack_fuel_per_q or 0.0) + (rec.labor_cost_per_quintal or 0.0) + (rec.depreciation_per_quintal or 0.0) + (rec.interest_per_quintal or 0.0) + (rec.other_cost_per_quintal or 0.0) + (rec.loading_cost_per_quintal or 0.0)
            rec.total_cost_per_quintal = total_per_q
            rec.total_cost_per_quintal = total_per_q

    def action_compute(self):
        for rec in self:
            rec._compute_totals()
            rec.state = 'computed'

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'
