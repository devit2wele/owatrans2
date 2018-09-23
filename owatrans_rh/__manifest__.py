# -*- coding: utf-8 -*-
{
    'name': "OWATRANS_rh_wele",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "FONGIP",
    'website': "http://www.fongip.sn",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': [
        'base',
        'hr',
        'hr_contract', 
        'hr_holidays',
        'report',
        'mail',
    ],

    # always loaded
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',  
        'views/templates.xml', 
        'data/fete_locale.xml', 
        'data/cron.xml',
        'report/owatrans_rh_report.xml',
        'report/presence_template.xml',
        'data/mail_template.xml',
    ],
    
    'qweb' : ['static/src/xml/qweb.xml'],

    
}
