{
    'name': 'Cost Estimation',
    'version': '18.0.1.0.0',
    'category': 'Manufacturing',
    'author': 'Natnael Yonas',
    'summary': 'Estimate cost per quintal for animal feed (layer, broiler).',
    'description': 'Manual feed cost estimation module porting Excel logic to Odoo.',
    'depends': ['base', 'product', 'account', 'mail'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'views/feed_config_views.xml',
        'views/feed_formula_views.xml',
        'views/feed_estimation_views.xml',
        'views/feed_reporting.xml',

        
        'views/feed_menus.xml',

        
        'reports/feed_estimation_report.xml',
        'reports/templates.xml',
        'data/feed_data.xml',
    ],
    'installable': True,
    'application': True,
}