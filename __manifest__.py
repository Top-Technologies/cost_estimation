{
    'name': 'Animal Feed Cost Estimation',
    'version': '1.0.0',
    'category': 'Manufacturing',
    'author': 'Natnael Yonas',
    'summary': 'Estimate cost per quintal for animal feed (layer, broiler).',
    'description': 'Manual feed cost estimation module porting Excel logic to Odoo 17.',
    'depends': ['base', 'product', 'account', 'mail'],

    'icon': 'static/description/icon2.png',
    # 'images': ['static/description/icon2.png'],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'reports/feed_estimation_report.xml',

        'views/feed_menus.xml',
        'views/feed_config_views.xml',
        'views/feed_formula_views.xml',
        'views/feed_estimation_views.xml',

        'reports/templates.xml',
        'data/feed_data.xml',
    ],
    'installable': True,
    'application': True,
}
