# -*- coding: utf-8 -*-
{
    'name': 'Owatrans Facturation',
    'version': '1.0',
    'category': 'SUPPLY',
    'description': """Owatrans Facturation""",
    'depends': [
        'base',
        'report',
        'mail',
        'sale',
        'owatrans_parc_automobile',
    ],
    'author': 'Aliou Samba WELE',
    'website': 'www.owatrans.com',
    'license': 'AGPL-3',
    'data': [
        'security/ir.model.access.csv',
        'views/owatrans_facturation_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'data/report_paperformat_data.xml',
        'report/external_layout.xml',
        'report/transport_reports.xml',
        'report/transport_quotation_templates.xml',
        'report/transport_order_templates.xml',
        'report/transport_test_templates.xml',
        'data/mail_template_data.xml',
    ],
    'demo': [

    ],
    'installable': True,
    'application': True,
}
