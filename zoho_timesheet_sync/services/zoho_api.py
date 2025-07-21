import requests
import logging
from odoo import api, models, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ZohoAPIService(models.TransientModel):
    _name = 'zoho.api.service'
    _description = 'Service API Zoho'

    def _get_zoho_config(self):
        """Récupère la configuration Zoho depuis les paramètres système"""
        config = self.env['ir.config_parameter'].sudo()
        return {
            'client_id': config.get_param('zoho.client_id'),
            'client_secret': config.get_param('zoho.client_secret'),
            'refresh_token': config.get_param('zoho.refresh_token'),
            'base_url': config.get_param('zoho.base_url', 'https://www.zohoapis.com')
        }

    def _get_access_token(self):
        """Obtient un token d'accès Zoho"""
        config = self._get_zoho_config()
        if not all([config['client_id'], config['client_secret'], config['refresh_token']]):
            raise UserError("Configuration Zoho incomplète")
        
        data = {
            'refresh_token': config['refresh_token'],
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post(
                'https://accounts.zoho.com/oauth/v2/token',
                data=data,
                timeout=30
            )
            response.raise_for_status()
            return response.json().get('access_token')
        except Exception as e:
            _logger.error(f"Erreur lors de l'obtention du token Zoho: {e}")
            raise UserError(f"Impossible d'obtenir le token Zoho: {e}")

    def sync_project_to_workdrive(self, project_id):
        """Synchronise un projet vers Zoho WorkDrive"""
        project = self.env['project.project'].browse(project_id)
        token = self._get_access_token()
        
        headers = {
            'Authorization': f'Zoho-oauthtoken {token}',
            'Content-Type': 'application/json'
        }
        
        folder_data = {
            'data': {
                'attributes': {
                    'name': project.name,
                    'description': project.description or ''
                }
            }
        }
        
        try:
            config = self._get_zoho_config()
            response = requests.post(
                f"{config['base_url']}/workdrive/api/v1/files",
                headers=headers,
                json=folder_data,
                timeout=30
            )
            response.raise_for_status()
            
            folder_info = response.json()
            project.write({
                'x_zoho_folder_id': folder_info.get('data', {}).get('id'),
                'x_sync_status': 'synced'
            })
            
            return True
            
        except Exception as e:
            _logger.error(f"Erreur sync WorkDrive: {e}")
            project.write({'x_sync_status': 'error'})
            return False

    def sync_task_to_cliq(self, task_id):
        """Synchronise une tâche vers Zoho Cliq"""
        task = self.env['project.task'].browse(task_id)
        project = task.project_id
        
        if not project.x_cliq_channel:
            _logger.warning(f"Pas de canal Cliq configuré pour le projet {project.name}")
            return False
            
        token = self._get_access_token()
        
        headers = {
            'Authorization': f'Zoho-oauthtoken {token}',
            'Content-Type': 'application/json'
        }
        
        message = f"🎯 Nouvelle tâche: {task.name}\n"
        message += f"📊 Priorité: {task.x_priority_score or 'Non définie'}\n"
        message += f"⏰ Heures planifiées: {task.planned_hours}h\n"
        message += f"👤 Assigné à: {task.user_ids[0].name if task.user_ids else 'Non assigné'}"
        
        cliq_data = {
            'text': message
        }
        
        try:
            config = self._get_zoho_config()
            response = requests.post(
                f"{config['base_url']}/cliq/api/v2/channels/{project.x_cliq_channel}/messages",
                headers=headers,
                json=cliq_data,
                timeout=30
            )
            response.raise_for_status()
            
            task.write({'x_last_sync': fields.Datetime.now()})
            return True
            
        except Exception as e:
            _logger.error(f"Erreur sync Cliq: {e}")
            return False