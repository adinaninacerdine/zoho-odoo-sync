from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ProjectProject(models.Model):
    _inherit = "project.project"

    x_zoho_folder_id = fields.Char(
        string="ID Dossier Zoho",
        help="WorkDrive folder ID for this project",
        copy=False
    )
    x_cliq_channel = fields.Char(
        string="Canal Cliq",
        help="Cliq channel name for this project",
        copy=False
    )
    x_sync_status = fields.Selection([
        ('pending', 'En attente'),
        ('synced', 'Synchronisé'),
        ('error', 'Erreur')
    ], string="Statut Synchronisation", 
       default='pending', 
       help="Current synchronization status with Zoho",
       copy=False)
    
    @api.constrains('x_zoho_folder_id')
    def _check_zoho_folder_id(self):
        """Valide le format de l'ID dossier Zoho"""
        for record in self:
            if record.x_zoho_folder_id and not record.x_zoho_folder_id.isalnum():
                raise ValidationError(_('Zoho folder ID must contain only alphanumeric characters'))
    
    @api.constrains('x_cliq_channel')
    def _check_cliq_channel(self):
        """Valide le format du canal Cliq"""
        for record in self:
            if record.x_cliq_channel and len(record.x_cliq_channel) > 50:
                raise ValidationError(_('Cliq channel name cannot exceed 50 characters'))