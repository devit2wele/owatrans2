# -*- coding: utf-8 -*-

from odoo import api, fields, models

class Partner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def __init__(self, pool, cr):

        init_res = super(Partner, self).__init__(pool, cr)
        # cr.execute("""
        # 	ALTER TABLE public.res_partner ADD COLUMN test character varying;
        # 	COMMENT ON COLUMN public.res_partner.test IS 'Test';
        # """)
        
        return init_res

    code_swift = fields.Char(string="Adresse SWIFT")
    cni = fields.Char(string="Numéro CNI")
    agent = fields.Boolean(string='Is a agent', help="Check this box if this contact is a agent. ")