# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta
from datetime import date
from dateutil.relativedelta import relativedelta

import email, getpass, imaplib, os
from email.header import decode_header
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
import socket
import base64

from random import randint

from odoo import api, fields, models, _
from odoo.tools import ustr
from odoo.exceptions import UserError
from odoo import SUPERUSER_ID


TYPE_POINTAGE = [
    ('entree', 'Entrée'),
    ('sortie_pause', 'Sortie Pause'),
    ('retour_pause', 'Retour Pause'),
    ('sortie', 'Sortie'),
]

HIDE = [
    ('DISPLAY', 'o'),
    ('NODISPLAY', 'n'),
]

class PointageManuel(models.Model):
    _name = "pointage.manuel"
    _description = "Pointage manuel"

    employee = fields.Many2one('hr.employee', string='Employee', required=True)
    type_pointage = fields.Selection(TYPE_POINTAGE, string='Type de pointage', required=True)
    date_heure = fields.Datetime(string='Date heure', required=True)
    date_pointage = fields.Date(String='Date Pointage', store=True, compute='_compute_date_and_heure_pointage')
    heure_pointage = fields.Char(String='Heure Pointage', store=True, compute='_compute_date_and_heure_pointage')
    presence_id = fields.Many2one('owatrans.presence', string='Presence')
    is_admin = fields.Boolean(compute='_compute_is_admin', store=True)

    @api.one
    @api.depends('date_heure')
    def _compute_date_and_heure_pointage(self):
        if self.date_heure:
            self.date_pointage, self.heure_pointage = self.date_heure.split(' ')[0], self.date_heure.split(' ')[1] 


    
    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, vals):
        res  =  super(PointageManuel, self).create(vals)
        return res

    @api.multi
    def write(self, vals):
        rep  =  super(PointageManuel, self).write(vals)
        return rep

class OwatransPresence(models.Model):
    _name = "owatrans.presence"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _description = "Liste de Presence"

    employee = fields.Many2one('hr.employee', string='Employee')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    diff_presence = fields.Float(string='Presence', compute='_compute_pointage_statistique', store=True)
    hide_diff_presence = fields.Selection(HIDE, store=True)
    pointage_manuel_ids = fields.One2many('pointage.manuel', 'presence_id', string='Presence', compute='_compute_pointage_statistique', store=True)
    current_user = fields.Boolean(defaut=True, store=True)


    @api.model
    def default_get(self, fields):
        res = super(OwatransPresence, self).default_get(fields)
        print 'test after create record'

        employee_is_related_user = self.env["hr.employee"] \
                                       .search([
                                            ('user_id', '=', self.env.user.id),
        ], limit=1)

        if 'employee' in fields and employee_is_related_user and self.env.user.id is not SUPERUSER_ID :
            res.update({
                'employee' : employee_is_related_user.id,
            })

        return res




    @api.depends('employee', 'date_from', 'date_to')
    def _compute_pointage_statistique(self):
        element = []
        if self.env.user.id is not SUPERUSER_ID:
            self.employee = self.env["hr.employee"] \
                                .search([
                                    ('user_id', '=', self.env.user.id),
            ], limit=1)


        if not self.employee and not self.date_from:
            self.hide_diff_presence = 'NODISPLAY'
            all_pointage_user = self.env["pointage.manuel"].search([])
            self.pointage_manuel_ids = all_pointage_user
            
        
        elif self.employee and not self.date_from:
            all_pointage_user = self.env["pointage.manuel"].search([('employee', '=', self.employee.id)])
            self.pointage_manuel_ids = all_pointage_user
            
        elif self.employee and self.date_from:
            self.hide_diff_presence = 'DISPLAY'
            #Par defaut on prend la date_from
            self.date_to = self.date_to or self.date_from
            date_from = datetime.strptime(self.date_from + ' ' + '08:00:00', '%Y-%m-%d %H:%M:%S')
            date_to = datetime.strptime(self.date_to + ' ' + '19:00:00', '%Y-%m-%d %H:%M:%S')
            all_pointage_user = self.env["pointage.manuel"] \
                                    .search([
                                        ('employee', '=', self.employee.id),
                                        ('date_heure', '>=', fields.Date.to_string(date_from)),
                                        ('date_heure', '<=', fields.Date.to_string(date_to)),
            ])

            self.pointage_manuel_ids = all_pointage_user
            
            #working time delta
            self.diff_presence = self.compute_working_time(date_from, date_to, self.employee.id)
            print self.diff_presence
            
        elif not self.employee and self.date_from:
            self.hide_diff_presence = 'NODISPLAY'
            self.date_to = self.date_to or self.date_from
            date_from = datetime.strptime(self.date_from + ' ' + '08:00:00', '%Y-%m-%d %H:%M:%S')
            date_to = datetime.strptime(self.date_to + ' ' + '19:00:00', '%Y-%m-%d %H:%M:%S')
            all_pointage_user = self.env["pointage.manuel"].search([
                ('date_heure', '>=', fields.Date.to_string(date_from)),
                ('date_heure', '<=', fields.Date.to_string(date_to)),
            ])
            self.pointage_manuel_ids = all_pointage_user


    @api.multi
    def compute_working_time(self,date_from, date_to, employee_id):
        working_time = 0
        FMT = '%H:%M:%S'

        while date_from <= date_to:
            str_date_from = str(date_from).split(' ')[0]
            entree=[]
            sortie=[]
            #ALL pointage
            pointage_all = self.env["pointage.manuel"] \
                               .search([
                                    ('employee', '=', employee_id),
                                    ('date_pointage', '=', str_date_from),
            ])
            if pointage_all:
                #On regroupe par categorie
                for pointage in pointage_all:
                    #type IN
                    if pointage.type_pointage in ['entree', 'retour_pause']:
                        entree.append(pointage.heure_pointage)
                    #type OUT
                    if pointage.type_pointage in ['sortie', 'sortie_pause']:
                        sortie.append(pointage.heure_pointage)
                if entree and sortie:
                    for index in range(min(len(entree), len(sortie))):
                        tdelta_day_work_time = datetime.strptime(sortie[index], FMT) - datetime.strptime(entree[index], FMT)
                        working_time += tdelta_day_work_time.total_seconds()/3600.0

            date_from = date_from + relativedelta(days=1)

        return working_time

    @api.multi
    def action_send_presence(self):
        self.ensure_one()
        
        ir_model_data = self.env['ir.model.data']
        
        try:
            template_id = ir_model_data.get_object_reference('owatrans_rh', 'email_template_edi_presence')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data.get_object_reference('mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_model': 'owatrans.presence',
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
    def action_print_presence(self):
        return self.env['report'].get_action(self, 'owatrans_rh.report_presence')

    @api.multi
    def send_mail_working_week(self):
        all_employees = self.env["hr.employee"].search([])
        today = datetime.today() #Jour de la semaine
        day_to_send_mail = today.weekday() #Lundi:0, Mardi:1, ..., Dimanche:6

        if today.weekday() == day_to_send_mail:
            #Deplacement du curseur à la semaine précédente (lundi)
            tdelta = timedelta(days=today.weekday(), weeks=1)
            #Lundi semaine passée
            date_from = today - tdelta
            #Vendredi semaine pasée
            date_to = date_from + timedelta(days=4)
            #Chaque employé on lui envoie statistiques
            for employee in all_employees:
                horaire = {}
                pointage_employee = {}
                work_date = {}
                i=0
                date_from_employee = date_from
                while date_from_employee <= date_to:
                    wk_time = self.compute_working_time(date_from_employee, date_from_employee, employee.id)
                    horaire[i] = wk_time
                    work_date[i] = str(date_from_employee).split(' ')[0]
                    pointage_employee[i] = self.get_horaire_employee(date_from_employee, employee.id)
                    i+=1
                    date_from_employee = date_from_employee + relativedelta(days=1)
                self.send_mail(horaire, pointage_employee, employee.work_email, date_from, date_to) if horaire and employee.work_email else None

    def get_horaire_employee(self, date, employee_id):

        #Heure d'entrée
        pointage_entree_time = self.env["pointage.manuel"] \
                                    .search([
                                        ('employee', '=', employee_id),
                                        ('date_pointage', '=', date),
                                        ('type_pointage', '=', 'entree')
        ], limit=1).heure_pointage
        #Heure Sortie pause
        pointage_sortie_pause_time = self.env["pointage.manuel"] \
                                         .search([
                                            ('employee', '=', employee_id),
                                            ('date_pointage', '=', date),
                                            ('type_pointage', '=', 'sortie_pause')
        ], limit=1).heure_pointage
        #Heure Retour Pause
        pointage_retour_pause_time = self.env["pointage.manuel"] \
                                         .search([
                                            ('employee', '=', employee_id),
                                            ('date_pointage', '=', date),
                                            ('type_pointage', '=', 'retour_pause')
        ], limit=1).heure_pointage
        #Heure descente
        pointage_sortie_time = self.env["pointage.manuel"] \
                                          .search([
                                            ('employee', '=', employee_id),
                                            ('date_pointage', '=', date),
                                            ('type_pointage', '=', 'sortie')
        ], limit=1).heure_pointage

        return {
            'entree': pointage_entree_time,
            'sortie_pause': pointage_sortie_pause_time,
            'retour_pause': pointage_retour_pause_time,
            'sortie': pointage_sortie_time,
        }



    @api.multi
    def chargement_donnees_test_pointage(self):
        """
        Job desactivité par defaut
        A lancer manuellement
        A utiliser pour charger des données de test (Pointage manuel semaine precedente)
        """

        liste_heure_entree = ['07:30:00', '08:00:00', '08:15:00', '08:30:00', '08:50:00', '09:00:00', '09:15:00', '09:30:00']
        liste_heure_sortie_pause = ['13:00:00', '13:05:00', '13:15:00', '13:30:00', '13:50:00', '13:45:00', '13:59:00', '13:55:00']
        liste_heure_retour_pause = ['14:00:00', '14:05:00', '14:15:00', '14:30:00', '14:50:00', '15:00:00', '15:15:00', '15:30:00']
        liste_heure_sortie = ['17:30:00', '18:00:00', '18:30:00', '18:45:00', '18:50:00', '19:00:00', '19:30:00', '20:30:00']
        today = datetime.today()

        tdelta = timedelta(days=today.weekday(), weeks=1)
        #Lundi semaine passée
        date_from = today - tdelta
        #Vendredi semaine passée
        date_to = date_from + timedelta(days=4)

        all_employees = self.env["hr.employee"].search([])
        for employee in all_employees:
                date_from_employee = date_from
                while date_from_employee <= date_to:
                    date_from_point_entree = str(date_from_employee).split(' ')[0] + ' ' + liste_heure_entree[randint(0, len(liste_heure_entree)-1)]
                    date_from_point_sortie_pause = str(date_from_employee).split(' ')[0] + ' ' + liste_heure_sortie_pause[randint(0, len(liste_heure_sortie_pause)-1)]
                    date_from_point_retour_pause = str(date_from_employee).split(' ')[0] + ' ' + liste_heure_retour_pause[randint(0, len(liste_heure_retour_pause)-1)]
                    date_from_point_sortie = str(date_from_employee).split(' ')[0] + ' ' + liste_heure_sortie[randint(0, len(liste_heure_sortie)-1)]
                    self.env['pointage.manuel'].create({
                                                    'employee': employee.id,
                                                    'type_pointage': 'entree',
                                                    'date_heure': date_from_point_entree,
                                                })
                    self.env['pointage.manuel'].create({
                                                    'employee': employee.id,
                                                    'type_pointage': 'sortie_pause',
                                                    'date_heure': date_from_point_sortie_pause,
                                                })
                    self.env['pointage.manuel'].create({
                                                    'employee': employee.id,
                                                    'type_pointage': 'retour_pause',
                                                    'date_heure': date_from_point_retour_pause,
                                                })
                    self.env['pointage.manuel'].create({
                                                    'employee': employee.id,
                                                    'type_pointage': 'sortie',
                                                    'date_heure': date_from_point_sortie,
                                                })
                    date_from_employee = date_from_employee + relativedelta(days=1)
                    

    def send_mail(self, horaire, pointage_employee, work_email, date_from, date_to):
        msg = MIMEMultipart('alternative')
        msg['From'] = 'export.iraiser@alima.ngo'
        msg['To'] = work_email
        recipients = msg['To'].split(',')
        week_time = sum([horaire[i] for i in range(len(horaire))])
            
        message = ''
        work_days = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi']

        msg['Subject'] = 'Working Time'

        message += '<head>'
        message +=  '<meta http-equiv="Content-Type" content="text/html; charset=utf-8">'
        message +=  '<title>html title</title>'
        message +=  '<style type="text/css" media="screen">'
        message +=          'table{background-color: #f7a604;empty-cells:hide;}'
        message +=          'td.cell{background-color: white;color: #025eaa;}'
        message +=          'p.image{background-color: #000;}'
        message +=  '</style>'
        message += '</head>'
        message +=  '<table style="border: blue 1px solid;">'

        message += '<tr align="center">'
        message +=   '<td>'+'semaine du ' +str(date_from).split(' ')[0]+ ' au ' +str(date_to).split(' ')[0]+ '</td>'
        message += '</tr>'

        message +=          '<tr>'
        message +=            '<td class="cell"></td>'
        for i in range(len(work_days)):
            message +=        '<td class="cell">' +work_days[i]+ '</td>'
        message +=          '</tr>'
        
        message +=          '<tr>'
        message +=            '<td class="cell">Entrée</td>'
        for i in range(len(horaire)):
            message +=        '<td class="cell">'+ str(pointage_employee[i]['entree']) +'</td>'
        message +=          '</tr>'

        message +=          '<tr>'
        message +=            '<td class="cell">Sortie pause</td>'
        for i in range(len(horaire)):
            message +=        '<td class="cell">'+ str(pointage_employee[i]['sortie_pause']) +'</td>'
        message +=          '</tr>'

        message +=          '<tr>'
        message +=            '<td class="cell">Retour pause</td>'
        for i in range(len(horaire)):
            message +=        '<td class="cell">'+ str(pointage_employee[i]['retour_pause']) +'</td>'
        message +=          '</tr>'

        message +=          '<tr>'
        message +=            '<td class="cell">Sortie</td>'
        for i in range(len(horaire)):
            message +=        '<td class="cell">'+ str(pointage_employee[i]['sortie']) +'</td>'
        message +=          '</tr>'

        message +=          '<tr>'
        message +=            '<td class="cell">Presence</td>'
        for i in range(len(horaire)):
            message +=        '<td class="cell">'+ str(horaire[i]) +'</td>'
        message +=          '</tr>'
        
        message +=  '</table">'
        message += '</body>'

        msg.attach(MIMEText(message, 'html'))

        mailserver = smtplib.SMTP('smtp.gmail.com:587')
        mailserver.ehlo()
        mailserver.starttls()
        mailserver.ehlo()
        mailserver.login('export.iraiser@alima.ngo', '@LIM@2017')
        mailserver.sendmail(msg['From'], recipients, msg.as_string())
        mailserver.quit()