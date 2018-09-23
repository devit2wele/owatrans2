# -*- coding: utf-8 -*-

from odoo import api, fields, models

class Franchise(models.Model):
    _name = 'owatrans.franchise'

    
    client_id = fields.Many2one('res.partner', string='Client', required=True)
    agent_id = fields.Many2one('res.partner', string='Agent', required=True)
    numero_tc = fields.Char(string="Numero TC")
    numero_compagnie = fields.Char(string="Numero Compagnie")
    numero_conteneur = fields.Char(string="Numero Conteneur")
    date_entree = fields.Date(string='Date d\'entrée')
    date_sortie = fields.Date(string='Date de sortie')
    vehicule = fields.Many2one('fleet.vehicle', string='Véhicule', required=True)