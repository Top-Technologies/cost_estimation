
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

    def _get_most_recent_purchase_price(self, product):
        """
        Get the most recent purchase order unit price for a product
        Only consider POs where the product has been received in inventory
        """
        if not product:
            return 0.0
        
        # Search for purchase order lines with received stock moves
        self.env.cr.execute("""
            SELECT pol.price_unit
            FROM purchase_order_line pol
            JOIN purchase_order po ON pol.order_id = po.id
            JOIN stock_move sm ON sm.purchase_line_id = pol.id
            WHERE pol.product_id = %s
              AND sm.state = 'done'
              AND po.state IN ('purchase', 'done')
              AND pol.price_unit > 0
            ORDER BY po.date_approve DESC, po.id DESC
            LIMIT 1
        """, (product.id,))
        
        result = self.env.cr.fetchone()
        if result:
            return result[0]
        
        # Fallback to standard cost if no recent purchase found
        return product.standard_price or 0.0

    @api.depends('input_kg','price_per_kg')
    def _compute_total(self):
        for rec in self:
            rec.total_cost = (rec.input_kg or 0.0) * (rec.price_per_kg or 0.0)
    
    @api.onchange('product_id')
    def _onchange_product(self):
        """When product is selected, fetch its unit and price from most recent purchase order"""
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
                
                # Get price from most recent purchase order with receipt
                # Fallback to standard cost if no purchase found
                line.price_per_kg = self._get_most_recent_purchase_price(line.product_id)
