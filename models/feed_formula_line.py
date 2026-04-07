
from odoo import models, fields, api

class FeedFormulaLine(models.Model):
    _name = 'feed.formula.line'
    _description = 'Feed Formula Line (components for a formula)'
    _order = 'sequence, id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    formula_id = fields.Many2one('feed.formula', string='Formula', ondelete='cascade', required=True)
    sequence = fields.Integer(string='Sequence', default=10, tracking=True)
    type = fields.Selection([('raw','Raw Material'), ('pack','Packing Material'), ('fuel','Fuel')], string='Type', required=True, default='raw', tracking=True)
    product_id = fields.Many2one(
        'product.product',
        string='Component',
        required=True
    )
    input_kg = fields.Float(string='Input', default=0.0, tracking=True)
    price_per_kg = fields.Float(string='Unit Price', default=0.0, tracking=True)
    total_cost = fields.Monetary(string='Total Cost', compute='_compute_total', store=True, currency_field='company_currency_id')
    company_currency_id = fields.Many2one('res.currency', string='Currency', related='formula_id.company_id.currency_id', readonly=True)

    @api.depends('input_kg','price_per_kg')
    def _compute_total(self):
        for rec in self:
            rec.total_cost = (rec.input_kg or 0.0) * (rec.price_per_kg or 0.0)
    
    @api.onchange('product_id')
    def _onchange_product(self):
        """When product is selected, fetch its unit and price from product master data"""
        for line in self:
            if line.product_id:
                # Fetch from product template
                product_template = line.product_id.product_tmpl_id
                
                # Get default unit from product (assuming KG is the unit)
                # You can modify this based on your product UOM configuration
                if product_template.uom_id:
                    # Convert to KG if needed
                    line.input_kg = line.product_id.uom_id._compute_quantity(1.0, product_template.uom_po_id)
                else:
                    line.input_kg = 1.0
                
                # Get cost price from product template cost field (standard_price)
                # This is the "Value of the product (automatically computed in AVCO)"
                line.price_per_kg = product_template.standard_price or 0.0
