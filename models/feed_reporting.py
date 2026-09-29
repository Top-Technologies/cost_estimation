from odoo import fields, models,api


class FeedReporting(models.Model):
    _name = 'feed.reporting'
    _description = 'Feed Reporting'

    name = fields.Char(string='Report Title', required=True)
    date = fields.Date(string='Date', default=fields.Date.context_today)