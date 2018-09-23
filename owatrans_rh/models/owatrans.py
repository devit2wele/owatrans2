# -*- coding: utf-8 -*-
import tempfile
import base64
import os
import xlrd
from xlrd import XLRDError
from odoo import models, fields, api
#from workalendar import *
from workalendar.africa import Algeria as Senegal
import json
import hashlib
import base64
import time
import hmac
from hashlib import sha1
import workdays
import math
from time import gmtime, strftime
from workdays import networkdays
from workdays import workday
from datetime import datetime, date, timedelta
from openerp import _
import requests
from odoo.exceptions import Warning, ValidationError

MESSAGE = "Bonjour, vous avez une nouvelle demande de congés en attente de validation dans l'ERP de OWATRANS"
MESSAGE2 = "Votre demande de congés vient d'etre validee. Bonne vacances"
MESSAGE3 = "Une demande de congés vient d'etre validée par l'administrateur générale"
TYPE_EMPLOYEE = [
    ('prestataire','prestataire'),
    ('stagiaire','Stagiaire'),
    ('temporaire','Temporaires'),
    ('journalier','Journalier'),
]
#Leaves Status
class HrEmployee(models.Model):
    _name = 'hr.employee'
    _inherit = 'hr.employee'
    max_leaves = fields.Integer(string='Maximum Allowed', help='This value is given by the sum of all holidays requests with a positive value.', default=100)
    taken_leaves = fields.Integer(string='Maximum Allowed', help='This value is given by the sum of all holidays requests with a positive value.',default=60)
    remaining_leaves = fields.Integer(string='Maximum Allowed', help='This value is given by the sum of all holidays requests with a positive value.', default=40)
    matricule_pointage = fields.Integer(string='Matricule pointage')
    color = fields.Integer(String = 'Color Index')
    type_employee = fields.Selection(TYPE_EMPLOYEE, string="Type")

    def pointage_entree(self):
        self.env['pointage.manuel'].create({
            'employee': self.id,
            'type_pointage': 'entree',
            'date_heure': str(datetime.today()),
        })

    def pointage_sortie_pause(self):
        self.env['pointage.manuel'].create({
            'employee': self.id,
            'type_pointage': 'sortie_pause',
            'date_heure': str(datetime.today()),
        })

    def pointage_retour_pause(self):
        self.env['pointage.manuel'].create({
            'employee': self.id,
            'type_pointage': 'retour_pause',
            'date_heure': str(datetime.today()),
        })

    def pointage_sortie(self):
        self.env['pointage.manuel'].create({
            'employee': self.id,
            'type_pointage': 'sortie',
            'date_heure': str(datetime.today()),
        })

#Categorie
class Categorie(models.Model):
    _name = 'owatrans_rh.categorie'
    name = fields.Char(string  = 'Catégorie')

#Statut
class Categorie(models.Model):
    _name = 'owatrans_rh.statut'
    name = fields.Char(string  = 'Statut')

#RH
class hr_contract(models.Model):
    _name = 'hr.contract'
    _inherit = 'hr.contract'
    statut_id = fields.Many2one('owatrans_rh.statut', string  = 'Statut')
    categorie_id = fields.Many2one('owatrans_rh.categorie', string  = 'Catégorie')
    nb_part = fields.Float(digits = (1,1), string = 'Nombre de parts')
    remunere = fields.Boolean(string = 'Rémunération')

    _sql_constraints = [
        ('uniq_name', 'unique(name)', "La référence du contrat existe déjà merci de choisir une autre référence!"),
    ]

#HolidaysStaus
class hr_holidays(models.Model):
    _name = 'hr.holidays.status'
    _inherit = 'hr.holidays.status'
    delai_soumission = fields.Integer(string = "Délai de soumission(en jours)")


#Holidays
class hr_holidays(models.Model):
    _name = 'hr.holidays'
    _inherit = 'hr.holidays'

    #date_from = fields.Date(string='Start Date', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, index=True, copy=False)
    #date_to = fields.Date(string='End Date', readonly=True, states={'draft': [('readonly', False)], 'confirm': [('readonly', False)]}, index=True, copy=False)
    state = fields.Selection([('draft', 'To Submit'), ('cancel', 'Cancelled'),('validation_sup', 'Validation Sup'),('validation_drh', 'Validation DRH'), ('refuse', 'Refused'),('confirm', 'Validation DGA'), ('validate1', 'Validation DG'), ('validate', 'Validée')],
            string = 'Status', readonly=True, track_visibility='onchange', copy=False, default = 'draft', 
            help='The status is set to \'To Submit\', when a holiday request is created.\
            \nThe status is \'To Approve\', when holiday request is confirmed by user.\
            \nThe status is \'Refused\', when holiday request is refused by manager.\
            \nThe status is \'Approved\', when holiday request is approved by manager.')
    color = fields.Integer(string = 'Color')

    max_leaves = fields.Float(compute='_compute_user_left_days', string='Maximum Allowed', help='This value is given by the sum of all holidays requests with a positive value.')
    leaves_taken = fields.Float(compute='_compute_user_left_days', string='Leaves Already Taken', help='This value is given by the sum of all holidays requests with a negative value.')
    remaining_leaves = fields.Float(compute='_compute_user_left_days', string='Remaining Leaves', help='Maximum Leaves Allowed - Leaves Already Taken')
    
    date_retraite = fields.Date(string='End Date', readonly=True, compute='_compute_date_retraite')
    
    def _compute_user_left_days(self):
        employee_id = self.env.context.get('employee_id') or self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1).id
        if employee_id:
            res = self.env['hr.holidays.status'].get_days(employee_id)
        else:
            res = {sid: {'max_leaves':0, 'leaves_taken':0, 'remaining_leaves':0} for sid in self.ids}
        for record in self.env['hr.holidays.status']:
            record.leaves_taken = res[record.id]['leaves_taken']
            record.remaining_leaves = res[record.id]['remaining_leaves']
            record.max_leaves = res[record.id]['max_leaves']
            if 'virtual_remaining_leaves' in res[record.id]:
                record.virtual_remaining_leaves = res[record.id]['virtual_remaining_leaves']  

    #Exclude weekends and holidays from leaves
    def _get_number_of_days(self, date_from, date_to, employee_id): 
        holidays = []
        cal =  Senegal()

        #Récupérer les dates de jours fériés validés
        jour_ferie_ids =  self.env['owatrans_rh.ferie'].search([])
        
        if jour_ferie_ids:
            for jour_ferie_id in jour_ferie_ids:
               date_ferie = self.env['owatrans_rh.ferie'].search_read([['id','=',jour_ferie_id.id]], ['date'])[0]['date']
               holidays.append(datetime.strptime(date_ferie,'%Y-%m-%d').date())
        
        dtf = datetime.strptime(date_from,'%Y-%m-%d %H:%M:%S')
        dtt = datetime.strptime(date_to,'%Y-%m-%d %H:%M:%S')
        
        year1 = str(dtf).split("-")[0]
        year2 = str(dtt).split("-")[0]
        
        for i in cal.holidays(int(year1)):
            holidays.append(i[0])
        
        if (year1 != year2): 
            for i in cal.holidays(int(year2)):
                holidays.append(i[0])
        
        diff_day = networkdays(dtf.date(), dtt.date(), holidays)
        
        return diff_day


    #Override the onchange method to call function
    @api.onchange('date_to')
    def _onchange_date_to(self):
        """ Update the number_of_days. """
        date_from = self.date_from
        date_to = self.date_to

        # date_to has to be greater than date_from
        if (date_from and date_to) and (date_from > date_to):
            raise Warning(_('The start date must be anterior to the end date.'))

        super(hr_holidays, self)._onchange_date_to()


    @api.onchange('date_from')
    def _onchange_date_from(self):
        """
        If there are no date set for date_to, automatically set one 8 hours later than
        the date_from.
        Also update the number_of_days.
        """
        date_from = self.date_from
        date_to = self.date_to

        # date_to has to be greater than date_from
        if (date_from and date_to) and (date_from > date_to):
            raise Warning(_('The start date must be anterior to the end date.'))

        super(hr_holidays, self)._onchange_date_from()



    # def send_email(self, subject, email_to, message, cr,uid,ids,context=None):
    #     values = {
    #         'subject': subject,
    #          'body_html': message,
    #          'email_to': email_to,
    #          'email_from': 'owatrans@owatrans.sn',
    #          }
    #       #---------------------------------------------------------------
    #     mail_obj = self.pool.get('mail.mail') 
    #     msg_id = mail_obj.create(cr, uid, values, context=context) 
    #     if msg_id: 
    #           mail_obj.send(cr, uid, [msg_id], context=context) 
    #     return True
  
    @api.model
    def create(self, values):
        
        if values.get('state') and values['state'] not in ['draft', 'confirm','validation_sup','validation_drh', 'cancel'] and not self.env.user.has_group('base.group_user'):
            raise Warning(_('You cannot set a leave request as \'%s\'. Contact a human resource manager.') % values.get('state'))
        
        return super(hr_holidays, self).create(values)

    @api.multi
    def write(self, vals):

        if vals.get('state') and vals['state'] not in ['draft', 'confirm','refuse','validation_sup','validation_drh', 'cancel'] and not self.env.user.has_group('base.group_user'):
            raise Warning(_('You cannot set a leave request as \'%s\'. Contact a human resource manager.') % vals.get('state'))
        
        return super(hr_holidays, self).write(vals)


    @api.one
    @api.constrains('date_from')
    def _check_date_from(self):
        print 'test 1', 
        today = str(strftime("%Y-%m-%d %H:%M:%S", gmtime()))
        print 'date form test', self.date_from
        if self.date_from:
             date_from = datetime.strptime((self.date_from.split(' ')[0] + " 00:00:00"), "%Y-%m-%d %H:%M:%S")
             print 'date_from', date_from
             intervalle =super(hr_holidays, self)._get_number_of_days(today, str(date_from), self.employee_id.id)
             holiday_name = self.holiday_status_id.name
             delai_soumission = self.holiday_status_id.delai_soumission
             if int(intervalle) < delai_soumission :
                #raise ValidationError("Vous ne pouvez pas soumettre une demande de %s en moins de %s jours de la date prévue de départ"%(holiday_name, delai_soumission))
                raise ValidationError("Vous ne pouvez pas soumettre une demande de ce type de congés en moins de %s jours de la date prévue de départ" % (self.holiday_status_id.delai_soumission))

    # def holidays_confirm(self, cr, uid, ids, context=None):
    #     for record in self.browse(cr, uid, ids, context=context):
    #         if record.employee_id and record.employee_id.parent_id:
    #             self.message_subscribe_users(cr, uid, [record.id], user_ids=[record.employee_id.parent_id.user_id.id], context=context)
    #             if record.employee_id.parent_id.mobile_phone:
    #                 self.send_sms(record.employee_id.parent_id.mobile_phone, MESSAGE)
    #                 subject = "Demande de congés en attente"
    #                 email_to = record.employee_id.parent_id.work_email
    #                 print(email_to)
    #             self.send_email(subject, email_to, MESSAGE, cr, uid, ids)
    #         state = 'validation_sup'
    #         if self.pool['res.users'].has_group(cr, record.employee_id.id, 'base.group_hr_manager'):
    #             state = 'confirm'
    #         if self.pool['res.users'].has_group(cr, record.employee_id.id, 'owatrans_rh.group_dp'):
    #             state = 'validation_drh'
    #         if self.pool['res.users'].has_group(cr, record.employee_id.id, 'owatrans_rh.group_sg'):
    #             state = 'validation_ag'
    #     return self.write(cr, uid, ids, {'state': state})  

    # def validation_sup(self, cr, uid, ids, context=None):
    #     for record in self.browse(cr, uid, ids, context=context):
    #         if record.employee_id and record.employee_id.parent_id and record.employee_id.parent_id.user_id:
    #             self.message_subscribe_users(cr, uid, [record.id], user_ids=[record.employee_id.parent_id.user_id.id], context=context)
    #         self.send_sms("77645792242", MESSAGE)
    #         subject = "Demande de congés en attente"
    #         email_to = "sadaga.mbacke@owatrans.sn"
    #         self.send_email(subject, email_to, MESSAGE, cr, uid, ids)
    #     return self.write(cr, uid, ids, {'state': 'validation_drh'})  

    # def validation_drh(self, cr, uid, ids, context=None):
    #     for record in self.browse(cr, uid, ids, context=context):
    #         if record.employee_id and record.employee_id.parent_id and record.employee_id.parent_id.user_id:
    #             self.message_subscribe_users(cr, uid, [record.id], user_ids=[record.employee_id.parent_id.user_id.id], context=context)
    #         self.send_sms("77645792223", MESSAGE)
    #         subject = "Demande de congés en attente"
    #         email_to = "souleymane.bassoum@owatrans.sn"
    #         self.send_email(subject, email_to, MESSAGE, cr, uid, ids)
    #     return self.write(cr, uid, ids, {'state': 'confirm'})  

    # def validation_dga(self, cr, uid, ids, context=None):
    #     print 'test 5'
    #     for record in self.browse(cr, uid, ids, context=context):
    #         if record.employee_id and record.employee_id.parent_id and record.employee_id.parent_id.user_id:
    #             self.message_subscribe_users(cr, uid, [record.id], user_ids=[record.employee_id.parent_id.user_id.id], context=context)
    #         self.send_sms("77645792222", MESSAGE)
    #         subject = "Demande de congés en attente"
    #         email_to = "doudou.ka@owatrans.sn"
    #         self.send_email(subject, email_to, MESSAGE, cr, uid, ids)
    #     return self.write(cr, uid, ids, {'state': 'validate1'})  

    # def validation_ag(self, cr, uid, ids, context=None):
    #     for record in self.browse(cr, uid, ids, context=context):
    #         if record.employee_id:
    #             employee_ids = []
    #             employee_ids.append(record.employee_id.id)
    #             employee_leaves = self.pool.get('hr.employee').browse(cr, uid, employee_ids, context=context)
    #             leaves =  {'taken_leaves':employee_leaves.taken_leaves, 'max_leaves':employee_leaves.max_leaves, 'remaining_leaves':employee_leaves.remaining_leaves}
    #             if record.type =="add":
    #                 leaves['max_leaves'] = leaves['max_leaves'] + record.number_of_days
    #                 leaves['remaining_leaves'] = leaves['remaining_leaves'] + record.number_of_days
    #             if record.type =="remove":
    #                 leaves['taken_leaves'] = leaves['taken_leaves'] - record.number_of_days
    #                 leaves['remaining_leaves'] = leaves['remaining_leaves'] + record.number_of_days
    #             self.pool.get('hr.employee').write(cr, uid, employee_ids, leaves)
    #             employee_leaves = self.pool.get('hr.employee').browse(cr, uid, employee_ids, context=context)
            
    #         self.send_sms(record.employee_id.mobile_phone, MESSAGE2)
    #         self.send_sms("77645792242", MESSAGE3)
    #         self.send_sms(record.employee_id.parent_id.mobile_phone, MESSAGE3)
    #         self.send_sms("77645792230", MESSAGE3)
    #         self.send_sms("77645792223", MESSAGE3)
    #         subject = "Demande de congés validée"
    #         email_to = "souleymane.bassoum@owatrans.sn"
    #         self.send_email(subject, email_to, MESSAGE3, cr, uid, ids)
    #         self.send_email(subject, record.employee_id.parent_id.work_email, MESSAGE3, cr, uid, ids)
    #         self.send_email(subject, record.employee_id.work_email, MESSAGE3, cr, uid, ids)
    #         self.send_email(subject, "sadaga.mbacke@owatrans.sn", MESSAGE3, cr, uid, ids)
    #     return self.holidays_validate(cr, uid, ids, context)  

    """def send_sms(self, number, message):
           data = {'msisdn': number, 'message' : message, 'app': "script_vote", 'titre': 'OWATRANS-RH'}
           if number:
              self.validate_number(number)
              prefixe = number[:1]
              if prefixe == "7":
                           number = '221'+number
              elif prefixe == "0":
                       number = number[2:]
              elif prefixe == "+":
                       number = number[1:]
              send_sms = requests.post('http://10.10.1.17:3000/sendsms', data =data) 
              print("test dave")
              print "sending sms to " + number + " succeeded"
           return True"""
    def validate_number(self, number):
       if number: 
           number =  number.replace(" ", "")
           number =  number.replace("-", "")
           number =  number.replace("/", "")
           number =  number.replace(".", "")
       return number
    
#JoursFériesLocaux

class JourFeriesLocaux(models.Model):
    _name = 'owatrans_rh.ferie'
    name = fields.Many2one('owatrans_rh.fete_locale', string ='Intitulé', required = True)
    date = fields.Date(string='Date', required = True)
    statut = fields.Selection([('provisoire', 'Provisoire'), ('confirme', 'Confirmé'), ('revolu', 'Révolu')], readonly = True, default = 'provisoire')
    observation = fields.Char(string  = 'Observation')
    
    @api.multi
    def validate(self, values): 
        return self.write({'statut': 'confirme'})

    def revolu(self):
        confirmed_ids = []
        print ("the job is done dave")
        self._cr.execute("select id, date from owatrans_rh_ferie where statut = 'confirme'")
        jour_ferie_ids = self._cr.dictfetchall()
        for jour_ferie_id in jour_ferie_ids:
            date_ferie = datetime.strptime(jour_ferie_id['date'], "%Y-%m-%d").date()
            if date_ferie < date.today():
               self._cr.execute("UPDATE owatrans_rh_ferie SET statut = 'revolu' where id = %d"%jour_ferie_id['id'])
        return True


class Fetelocale(models.Model):
    _name = 'owatrans_rh.fete_locale'
    name = fields.Char(string  = 'Intitulé', required = True)
    type_fete = fields.Selection([('fete_religieuse', u'Fête réligieuse'), ('decret', u'Décret'), ('autre', 'Autre')])

class JourFeriesLocaux(models.Model):
    _name = 'owatrans_rh.ferie'
    name = fields.Many2one('owatrans_rh.fete_locale', string ='Intitulé', required = True)
    date = fields.Date(string='Date', required = True)
    statut = fields.Selection([('provisoire', 'Provisoire'), ('confirme', 'Confirmé'), ('revolu', 'Révolu')], readonly = True, default = 'provisoire')
    observation = fields.Char(string  = 'Observation')
