from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = "project.project"

    x_zoho_folder_id = fields.Char("ID Dossier Zoho")
    x_cliq_channel = fields.Char("Canal Cliq")
    x_sync_status = fields.Selection([
        ('pending', 'En attente'),
        ('synced', 'Synchronisé'),
        ('error', 'Erreur')
    ], string="Statut Synchronisation", default='pending')