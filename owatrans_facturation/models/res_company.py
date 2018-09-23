# -*- coding: utf-8 -*-

from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    ninea = fields.Char(string='NINEA')
    boite_postale = fields.Char(string='BP')