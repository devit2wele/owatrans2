# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo import api, fields, models, _
from odoo.tools import ustr
from odoo.exceptions import UserError
import odoo.addons.decimal_precision as dp




class PurchaseOrder(models.Model):

    _inherit = 'purchase.order'

    # def __init__(self, pool, cr):

    #     cr.execute("""
    #     	UPDATE public.ir_ui_menu
   	# 		SET name='Gestion des Appro'
 			# WHERE name='Purchases';
    #     """)
        
    #     return super(PurchaseOrder, self).__init__(pool, cr)
    
    
class PurchaseOrderLine(models.Model):
    
    _inherit = 'purchase.order.line'



class ProductTemplate(models.Model):

    _inherit = 'product.template'



class ProductProduct(models.Model):

    _inherit = 'product.product'


class ProductCategory(models.Model):
    _inherit = "product.category"


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'



# class Validation(models.Model):
#     _name = 'supply.alima.validation'
#     _description = 'Etat validation'
#     _order = "ordre_validation"
