from odoo import models, fields, api, _
from odoo.exceptions import UserError


class FeedEstimation(models.Model):
    _name = 'feed.estimation'
    _description = 'Feed Cost Estimation'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', required=True,
                       copy=False, default='New')
    formula_id = fields.Many2one(
        'feed.formula', string='Formula', required=True, tracking=True)
    config_id = fields.Many2one(
        'feed.config',
        string='Configuration',
        required=True,
        tracking=True
    )
    reported_by = fields.Many2one(
        'res.users',
        string='Reported By',
        default=lambda self: self.env.user,
        readonly=True,
        tracking=True
    )
    company_id = fields.Many2one(
        'res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
    date = fields.Date(default=fields.Date.context_today)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('computed', 'Computed'),
            ('submitted', 'Submitted'),
            ('needs_update', 'Needs Update'),
            ('approved', 'Approved')
        ],
        default='draft',
        tracking=True
    )
    # Approval fields
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, tracking=True, readonly=True)
    approver_id = fields.Many2one('res.users', string='Approver', readonly=True, tracking=True)
    approval_date = fields.Datetime(string='Approval Date', readonly=True, tracking=True)
    responsible_user_id = fields.Many2one('res.users', string='Responsible User', tracking=True, help='User responsible for approval')


    is_editable = fields.Boolean(
        string="Editable",
        default=True
    )

    is_reporter = fields.Boolean(
    compute="_compute_is_reporter",
    store=False
    )

    is_responsible = fields.Boolean(
        compute="_compute_is_responsible",
        store=False
    )

    was_submitted = fields.Boolean(
        string="Was Submitted",
        default=False
    )


    # configurable but copied from config on create
    total_quintal_daily = fields.Float(
        string='Daily Produced', default=400.0)
    standard_machine_capacity_q_per_day = fields.Float(
        string='Standard Machine Capacity (Q/day)', default=1800)
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
        string='Repair & Maintenance Total', currency_field='currency_id')

    # Loading cost input (per quintal) - user gives loading cost per Q (currency/Q)
    loading_cost_per_quintal_input = fields.Monetary(
        string='Loading Cost / Q (input)', currency_field='currency_id', help='User-provided loading cost per quintal (currency per Q)')

    # computed fields for loading
    monthly_loading_cost = fields.Monetary(
        string='Monthly Loading Cost', compute='_compute_totals', store=True, currency_field='currency_id')
    daily_loading_cost = fields.Monetary(
        string='Daily Loading Cost', compute='_compute_totals', store=True, currency_field='currency_id')

    line_ids = fields.One2many(
        'feed.estimation.line', 'estimation_id', string='Materials', tracking=True)

    # fuel total
    fuel_total = fields.Monetary(
        string='Fuel Total', compute='_compute_totals', store=True, currency_field='currency_id')

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

    # Selling Margin Analysis
    margin_percent = fields.Float(
        string='Target Margin (%)',
        default=0.0
    )

    cost_for_margin = fields.Float(
        string='Total Cost',
        compute='_compute_margin_analysis',
        store=True
    )

    profit_amount = fields.Float(
        string='Profit Amount',
        compute='_compute_margin_analysis',
        store=True
    )

    selling_price = fields.Float(
        string='Selling Price',
        compute='_compute_margin_analysis',
        store=True
    )

    responsible_user = fields.Many2many(
        'res.users',
        string='Responsible Users',
        required=True
    )

    def _get_annual_produced_quintal(self, rec):
        return (rec.total_quintal_daily or 0.0) * (rec.annual_working_days or 1)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle default values and add creator as follower"""
        records = super().create(vals_list)
        
        for record in records:
            # Add creator as follower
            if record.user_id and record.user_id.partner_id.id not in record.message_follower_ids.partner_id.ids:
                record.message_subscribe(partner_ids=[record.user_id.partner_id.id])
            
            # copy defaults from config - override defaults with config values
            config = record.config_id

            if config:
                # Always override with config values, not just if empty
                record.total_quintal_daily = config.daily_produced_q
                record.standard_machine_capacity_q_per_day = config.standard_machine_capacity_q_per_day
                record.annual_working_days = config.annual_working_days
                record.monthly_working_days = config.monthly_working_days
                record.interest_rate = config.interest_rate_percent
                record.labor_salary_monthly = config.labor_salary_monthly_config
                record.machine_price = config.machine_price_config
                record.loan_amount = config.loan_amount_config
                record.last_10m_rm_total = config.last_10m_rm_total_config
                record.loading_cost_per_quintal_input = config.loading_cost_per_quintal_input_config

            if record.name == 'New':
                record.name = self.env['ir.sequence'].next_by_code(
                    'feed.estimation') or '/'

            # If formula has components and estimation has no manual lines, populate lines from formula (copy)
            if record.formula_id and not record.line_ids:
                lines_to_create = []
                for fl in record.formula_id.line_ids:
                    lines_to_create.append((0, 0, {
                        'type': fl.type,
                        'product_id': fl.product_id.id,
                        'input_kg': fl.input_kg,
                        'price_per_kg': fl.price_per_kg,
                    }))
                if lines_to_create:
                    record.line_ids = lines_to_create
        return records

    def write(self, vals):
        # Check if config_id is being updated
        if 'config_id' in vals and vals['config_id']:
            config = self.env['feed.config'].browse(vals['config_id'])
            if config:
                # Update config-related fields when config changes
                vals.update({
                    'total_quintal_daily': config.daily_produced_q,
                    'standard_machine_capacity_q_per_day': config.standard_machine_capacity_q_per_day,
                    'annual_working_days': config.annual_working_days,
                    'monthly_working_days': config.monthly_working_days,
                    'interest_rate': config.interest_rate_percent,
                    'labor_salary_monthly': config.labor_salary_monthly_config,
                    'machine_price': config.machine_price_config,
                    'loan_amount': config.loan_amount_config,
                    'last_10m_rm_total': config.last_10m_rm_total_config,
                    'loading_cost_per_quintal_input': config.loading_cost_per_quintal_input_config,
                })

        return super().write(vals)

    @api.onchange('formula_id')
    def _onchange_formula(self):
        """When user selects a formula in the Estimation form, prefill lines from formula.
           This is client-side and won't persist unless the user saves the record."""
        for rec in self:
            if rec.formula_id:
                # If estimation already has lines, update them instead of adding new ones
                if rec.line_ids:
                    # Map existing lines by product for updating
                    existing_lines = {}
                    for line in rec.line_ids:
                        if line.product_id:
                            existing_lines[line.product_id.id] = line

                    # Update existing lines with formula data
                    lines_to_update = []
                    for fl in rec.formula_id.line_ids:
                        if fl.product_id.id in existing_lines:
                            # Update existing line
                            existing_lines[fl.product_id.id].update({
                                'type': fl.type,
                                'input_kg': fl.input_kg,
                                'price_per_kg': fl.price_per_kg,
                            })
                            lines_to_update.append(
                                existing_lines[fl.product_id.id])

                    # Remove lines that are not in new formula
                    lines_to_remove = [line for line in rec.line_ids
                                       if line.product_id and line.product_id.id not in [fl.product_id.id for fl in rec.formula_id.line_ids]]
                    if lines_to_remove:
                        rec.line_ids = [(2, line.id)
                                        for line in lines_to_remove]

                    # Add new lines for products not in existing
                    existing_product_ids = [
                        line.product_id.id for line in rec.line_ids if line.product_id]
                    new_formula_product_ids = [
                        fl.product_id.id for fl in rec.formula_id.line_ids]
                    new_products = [fl for fl in rec.formula_id.line_ids
                                    if fl.product_id.id not in existing_product_ids]

                    if new_products:
                        for fl in new_products:
                            rec.line_ids = [(0, 0, {
                                'type': fl.type,
                                'product_id': fl.product_id.id,
                                'input_kg': fl.input_kg,
                                'price_per_kg': fl.price_per_kg,
                            })]
                else:
                    # No existing lines, create new ones from formula
                    lines_to_set = []
                    for fl in rec.formula_id.line_ids:
                        lines_to_set.append((0, 0, {
                            'type': fl.type,
                            'product_id': fl.product_id.id,
                            'input_kg': fl.input_kg,
                            'price_per_kg': fl.price_per_kg,
                        }))
                    rec.line_ids = lines_to_set

    @api.onchange('config_id')
    def _onchange_load_config(self):

        for rec in self:
            if rec.config_id:

                config = rec.config_id

                rec.total_quintal_daily = config.daily_produced_q
                rec.standard_machine_capacity_q_per_day = config.standard_machine_capacity_q_per_day
                rec.annual_working_days = config.annual_working_days
                rec.monthly_working_days = config.monthly_working_days
                rec.interest_rate = config.interest_rate_percent
                rec.machine_price = config.machine_price_config
                rec.labor_salary_monthly = config.labor_salary_monthly_config
                rec.loan_amount = config.loan_amount_config
                rec.last_10m_rm_total = config.last_10m_rm_total_config
                rec.loading_cost_per_quintal_input = config.loading_cost_per_quintal_input_config

    @api.model
    def default_get(self, fields_list):

        res = super().default_get(fields_list)

        config = self.env['feed.config'].search(
            [('is_default', '=', True)],
            limit=1
        )

        if config:
            res['config_id'] = config.id

        return res

    @api.depends('line_ids.total_cost', 'labor_salary_monthly', 'machine_price', 'loan_amount', 'interest_rate', 'last_10m_rm_total', 'total_quintal_daily', 'annual_working_days', 'monthly_working_days', 'loading_cost_per_quintal_input', 'standard_machine_capacity_q_per_day')
    def _compute_totals(self):
        for rec in self:
            # Sum lines
            raw_total = sum(
                l.total_cost for l in rec.line_ids if l.type == 'raw')
            pack_total = sum(
                l.total_cost for l in rec.line_ids if l.type == 'pack')
            fuel_total = sum(
                l.total_cost for l in rec.line_ids if l.type == 'fuel')

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
            config = rec.config_id
            dep_percent = (config.depreciation_percent or 20.0) / 100.0
            total_depr_amount = (rec.machine_price or 0.0) * dep_percent
            annual_produced_q = self._get_annual_produced_quintal(rec) or 1.0
            dep_pre = (rec.total_quintal_daily or 0.0) / (rec.standard_machine_capacity_q_per_day or 1.0)
            depr_per_q = (total_depr_amount * dep_pre) / annual_produced_q
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
            rm_pack_fuel_total_adjusted = (
                raw_total_adjusted + pack_total + fuel_total)
            rm_pack_fuel_per_q = (rm_pack_fuel_total_adjusted)

            total_per_q = (rm_pack_fuel_per_q or 0.0) + (rec.labor_cost_per_quintal or 0.0) + (rec.depreciation_per_quintal or 0.0) + (
                rec.interest_per_quintal or 0.0) + (rec.other_cost_per_quintal or 0.0) + (rec.loading_cost_per_quintal or 0.0)
            rec.total_cost_per_quintal = total_per_q

    @api.depends('total_cost_per_quintal', 'margin_percent')
    def _compute_margin_analysis(self):
        for rec in self:

            cost = rec.total_cost_per_quintal or 0.0
            margin = (rec.margin_percent or 0.0) / 100.0

            rec.cost_for_margin = cost

            if margin >= 1:
                rec.profit_amount = 0.0
                rec.selling_price = 0.0
                continue

            if margin > 0:
                selling = cost * (1 + margin)
                profit = selling - cost
            else:
                selling = cost
                profit = 0.0

            rec.profit_amount = profit
            rec.selling_price = selling

    def action_compute(self):
        for rec in self:
            rec._compute_totals()
            rec.state = 'computed'

    def action_submit(self):
        """Submit for approval"""
        if not self.responsible_user_id:
            raise UserError('Please select a responsible user for approval.')
        
        self.state = 'submitted'
        
        # Add responsible user as follower to ensure they receive activities
        if self.responsible_user_id.partner_id.id not in self.message_follower_ids.partner_id.ids:
            self.message_subscribe(partner_ids=[self.responsible_user_id.partner_id.id])
        
        # Schedule activity for responsible user
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=self.responsible_user_id.id,
            summary=f'Feed Estimation {self.name} - Approval Required',
            note=f'Feed Estimation {self.name} has been submitted for your approval. Please review and approve or reject the estimation.'
        )

    def action_approve(self):
        """Approve the estimation"""
        if self.responsible_user_id != self.env.user:
            raise UserError('Only the responsible user can approve this estimation.')
        
        self.write({
            'state': 'approved',
            'approver_id': self.env.user.id,
            'approval_date': fields.Datetime.now()
        })
        
        # Schedule activity for creator
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=self.user_id.id,
            summary=f'Feed Estimation {self.name} - Approved',
            note=f'Your Feed Estimation {self.name} has been approved by {self.env.user.name}. Approval Date: {fields.Datetime.now()}'
        )

    def action_reject(self):
        """Reject the estimation and send back for update"""
        if self.responsible_user_id != self.env.user:
            raise UserError('Only the responsible user can reject this estimation.')
        
        self.state = 'needs_update'
        
        # Schedule activity for creator
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=self.user_id.id,
            summary=f'Feed Estimation {self.name} - Needs Update',
            note=f'Your Feed Estimation {self.name} has been rejected and needs updates. Rejected by: {self.responsible_user_id.name}. Date: {fields.Datetime.now()}'
        )

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = 'draft'
        
