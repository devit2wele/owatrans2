# -*- coding: utf-8 -*-

from datetime import date
from datetime import datetime

from odoo import api, fields, models, _
from odoo.tools import ustr
from odoo.exceptions import UserError




TYPE_CONTAINER = [
    ("type_20", "20'"),
    ("type_40", "40'"),
]

STATES = [
    ('draft', 'Brouillon'),
    ('confirmer', 'Confirmé'),
    ('annuler', 'annulé'),
]

NOTIFICATION = [
    ('draft', 'Brouillon'),
    ('sent_rq', 'RQ Envoyé'),
    ('re_sent_rq', 'RQ ré-envoyé'),
    ('print', 'Imprimer RQ'),
    ('sent_to', 'TO Envoyé'),
]

TYPE = [
    ('positionnement', 'POSITIONNEMENT'),
    ('import', 'IMPORT'),
    ('transport', 'TRANSPORT'),
]

CATEGORIE = [
    ('dry','DRY'),
    ('dry_high_cube', 'DRY HIGH CUBE'),
    ('open_top', 'OPEN TOP'),
    ('reefer', 'REEFER'),
    ('flat_rack', 'FLAT RACK'),
]

# ---------------------------------------------------------
# Zone
# ---------------------------------------------------------
class OwatransZone(models.Model):
    _name = "owatrans.zone"
    _description = "Zone"

    @api.depends('price_ht_20','price_ht_40')
    def compute_price_ttc(self):
        for rec in self:
            if rec.price_ht_20:
                rec.price_ttc_20 = rec.price_ht_20 * 1.18
            if rec.price_ht_40:
                rec.price_ttc_40 = rec.price_ht_40 * 1.18

    name = fields.Char(string='Destination', required=True)
    distance = fields.Integer(string='Kilométrage', required=True)
    date = fields.Date(string='Date')

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,\
        default=lambda self: self.env.user.company_id.currency_id.id)

    price_ht_20 = fields.Monetary(string='Montant HT', required=True)
    price_ht_40 = fields.Monetary(string='Montant HT', required=True)
    price_ttc_20 = fields.Monetary(string='Montant TTC', required=True, compute='compute_price_ttc')
    price_ttc_40 = fields.Monetary(string='Montant TTC', required=True, compute='compute_price_ttc')

    zone_line = fields.One2many('owatrans.zone.line', 'zone_id', string='Zone Line', readonly=True, store=True)



    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):

        data = {
            'date': datetime.today(),
            'price_ht_20': vals.get('price_ht_20'),
            'price_ht_40': vals.get('price_ht_40'),
            'price_ttc_20': vals.get('price_ttc_20'),
            'price_ttc_40': vals.get('price_ttc_40'),
        }
        vals['zone_line'], vals['date'] = [(0, 0, data)], date.today()

        return super(OwatransZone, self).create(vals)

    @api.multi
    def write(self, vals):

        if vals.get('price_ht_20') or vals.get('price_ht_40') or vals.get('price_ttc_20') or vals.get('price_ttc_40'):
            
            vals['price_ht_20'] = vals.get('price_ht_20') if vals.get('price_ht_20') else self.price_ht_20   
            vals['price_ht_40'] = vals.get('price_ht_40') if vals.get('price_ht_40') else self.price_ht_40   
            vals['price_ttc_20'] = vals.get('price_ttc_20') if vals.get('price_ttc_20') else self.price_ttc_20   
            vals['price_ttc_40'] = vals.get('price_ttc_40') if vals.get('price_ttc_40') else self.price_ttc_40   

            data = {
                'date':datetime.today(),
                'price_ht_20':vals.get('price_ht_20'),
                'price_ht_40':vals.get('price_ht_40'),
                'price_ttc_20': vals.get('price_ttc_20'),
                'price_ttc_40': vals.get('price_ttc_40'),
            }
            vals['zone_line'], vals['date'] = [(0, 0, data)], date.today()

        return super(OwatransZone, self).write(vals)

class OwatransZoneLine(models.Model):
    _name = "owatrans.zone.line"
    _description = "Zone Line"

    @api.multi
    @api.depends('zone_line')
    def compute_numero_rdv(self):
        for zone in self.mapped('zone_id'):
            number = 1
            for line in zone.zone_line:
                line.sequence =  str(number)
                number += 1


    sequence = fields.Char(readonly=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,\
        default=lambda self: self.env.user.company_id.currency_id.id)

    price_ht_20 = fields.Monetary(string='Montant HT 20')
    price_ht_40 = fields.Monetary(string='Montant HT 40')
    price_ttc_20 = fields.Monetary(string='Montant TTC 20')
    price_ttc_40 = fields.Monetary(string='Montant TTC 20')
    date = fields.Datetime(string='Date')

    zone_id = fields.Many2one('owatrans.zone', string='Zone')
    

    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        res  =  super(OwatransZoneLine, self).create(vals)        
        return res

    @api.multi
    def write(self, vals):
        rep  =  super(OwatransZoneLine, self).write(vals)
        return rep



class TransportOrder(models.Model):
    _name = "transport.order"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Transport Order"

    @api.depends('order_line.price_total')
    def _amount_all(self):
        for order in self:
            amount_total = 0.0
            for line in order.order_line:
                amount_total += line.price_total 
            order.amount_total = amount_total
                

    name = fields.Char(string='Connaissement', required=True)
    type = fields.Selection(TYPE, string='Type', required=True)
    partner_id = fields.Many2one('res.partner', string='Client', required=True)
    origin = fields.Char(string="Origine")
    date = fields.Date(string="Date")
    state = fields.Selection(STATES, default="draft")
    notification = fields.Selection(NOTIFICATION, default="draft")
    notes = fields.Text('Terms and Conditions')

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,\
        default=lambda self: self.env.user.company_id.currency_id.id)

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True)
    amount_total = fields.Monetary(string='Total', store=True, compute="_amount_all")

    order_line = fields.One2many('transport.order.line', 'order_id', string='Order Lines', copy=True)

    create_uid = fields.Many2one('res.users', 'Responsible')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.user.company_id.id)

    _sql_constraints = [
        ('uniq_name', 'unique(name)', "A transport order already exists with this Connaissement . OT's connaissement must be unique!"),
    ]

    @api.multi
    def unlink(self):
        for res in self:
            if res.state != 'annuler':
                raise UserError(_("Vous devez d'abord annuler la commande!"))
        return super(TransportOrder, self).unlink()


    @api.multi
    def action_confirm(self):
        self.state = 'confirmer'

    @api.multi
    def action_annuler(self):
        self.state = 'annuler'

    @api.multi
    def action_draft(self):
        self.state = self.notification = 'draft'

    
    @api.multi
    def action_send_rq(self):

        self.ensure_one()
        
        ir_model_data = self.env['ir.model.data']
        
        try:
            if self.state in ['draft',]:
                template_id = ir_model_data.get_object_reference('owatrans_facturation', 'email_template_edi_transport')[1]
            else:
                template_id = ir_model_data.get_object_reference('owatrans_facturation', 'email_template_edi_transport_done')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'transport.order',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
        })
        
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }


    @api.multi
    def action_re_send_rq(self):
        return self.action_send_rq()
    
    @api.multi
    def action_print_rq(self):
        self.write({'notification': "print"})
        return self.env['report'].get_action(self, 'owatrans_facturation.report_transportquotation')
    @api.multi
    def action_print_to(self):
        return self.env['report'].get_action(self, 'owatrans_facturation.report_transportorder')
    
    @api.multi
    def action_sent_to(self):
        self.notification = 'sent_to'
        return self.action_send_rq()

    @api.multi
    def is_with_taxe(self):
        if self.type == 'positionnement':
            return False
        return True

class TransportOrderLine(models.Model):
    _name = "transport.order.line"
    _description = "Transport Order Line"

    @api.depends('zone_sempos', 'type_container', 'order_id.type')
    def _compute_amount(self):
        for res in self:
            if res.zone_sempos and res.type_container and self.mapped('order_id').type:
                if self.mapped('order_id').type == 'positionnement':
                    if res.type_container == 'type_20':
                        res.price_total = res.zone_sempos.price_ht_20
                    if res.type_container == 'type_40':
                        res.price_total = res.zone_sempos.price_ht_40
                else:
                    if res.type_container == 'type_20':
                        res.price_total = res.zone_sempos.price_ttc_20
                    if res.type_container == 'type_40':
                        res.price_total = res.zone_sempos.price_ttc_40


    numero = fields.Char(string="Numéro", required=True)
    type_container = fields.Selection(TYPE_CONTAINER)
    zone_sempos = fields.Many2one('owatrans.zone', string='Zone Sempos', required=True)
    produit_type = fields.Many2one('type.produit', string='Type Produit', required=True)
    destination = fields.Char(string='Destination', required=True)
    categorie = fields.Selection(CATEGORIE, string='Catégorie')

    currency_id = fields.Many2one('res.currency', 'Currency', required=True,\
        default=lambda self: self.env.user.company_id.currency_id.id)

    price_total = fields.Monetary(string='Price', store=True, compute="_compute_amount")
    
    order_id = fields.Many2one('transport.order', string='Transport Order', index=True, required=True, ondelete='cascade')


class TypeProduit(models.Model):
    _name = "type.produit"
    _description = "Type produit"

    name = fields.Char(string="Type Produit", required=True)

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    def send_mail(self, auto_commit=False):
        if self._context.get('default_model') == 'transport.order' and self._context.get('default_res_id'):
            if not self.filtered('subtype_id.internal'):
                order = self.env['transport.order'].browse([self._context['default_res_id']])
                if order.notification == 'draft':
                    order.notification = 'sent_rq'
                if order.notification == 'sent_rq':
                    order.notification = 're_sent_rq'
        return super(MailComposeMessage, self.with_context(mail_post_autofollow=True)).send_mail(auto_commit=auto_commit)
