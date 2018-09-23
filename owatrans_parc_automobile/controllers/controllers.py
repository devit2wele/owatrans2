# -*- coding: utf-8 -*-
from odoo import http

# class OwatransParcAutomobile(http.Controller):
#     @http.route('/owatrans_parc_automobile/owatrans_parc_automobile/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/owatrans_parc_automobile/owatrans_parc_automobile/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('owatrans_parc_automobile.listing', {
#             'root': '/owatrans_parc_automobile/owatrans_parc_automobile',
#             'objects': http.request.env['owatrans_parc_automobile.owatrans_parc_automobile'].search([]),
#         })

#     @http.route('/owatrans_parc_automobile/owatrans_parc_automobile/objects/<model("owatrans_parc_automobile.owatrans_parc_automobile"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('owatrans_parc_automobile.object', {
#             'object': obj
#         })