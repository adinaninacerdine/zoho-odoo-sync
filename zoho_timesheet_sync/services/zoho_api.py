import requests
import logging
import time
from datetime import datetime, timedelta
from odoo import api, models, fields, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class ZohoAPIService(models.TransientModel):
    _name = 'zoho.api.service'
    _description = 'Service API Zoho'
    
    # Configuration par défaut sécurisée
    _zoho_timeout = 30
    _zoho_retries = 3

    def _get_zoho_config(self):
        """Récupère la configuration Zoho depuis les paramètres système"""
        config = self.env['ir.config_parameter'].sudo()
        zoho_config = {
            'client_id': config.get_param('zoho.client_id'),
            'client_secret': config.get_param('zoho.client_secret'),
            'refresh_token': config.get_param('zoho.refresh_token'),
            'workdrive_base_url': config.get_param('zoho.workdrive_base_url', 'https://www.zohoapis.com'),
            'cliq_base_url': config.get_param('zoho.cliq_base_url', 'https://cliq.zoho.com'),
            'token_url': config.get_param('zoho.token_url', 'https://accounts.zoho.com/oauth/v2/token')
        }
        
        # Validation de la configuration
        if not all([zoho_config['client_id'], zoho_config['client_secret']]):
            raise ValidationError(_('Zoho configuration is incomplete. Please configure client_id and client_secret.'))
        
        return zoho_config

    def _make_http_request(self, method, url, headers=None, data=None, json=None, params=None):
        """Effectue une requête HTTP avec retry et gestion d'erreur améliorée"""
        if headers is None:
            headers = {}
        
        # Set Content-Type for form data requests (OAuth token operations)
        if data is not None and 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        
        for attempt in range(self._zoho_retries):
            try:
                response = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=data,
                    json=json,
                    params=params,
                    timeout=self._zoho_timeout
                )
                
                if not response.ok:
                    _logger.warning("Zoho API error %s for %s %s: %s", 
                                  response.status_code, method, url, response.text)
                
                response.raise_for_status()
                return response
                
            except requests.RequestException as e:
                if attempt == self._zoho_retries - 1:
                    raise
                
                wait_time = (2 ** attempt) * 1
                _logger.info(f"Retrying request in {wait_time}s (attempt {attempt + 1})")
                time.sleep(wait_time)

    def _get_access_token(self):
        """Obtient un token d'accès Zoho avec validation"""
        config = self._get_zoho_config()
        
        if not config.get('refresh_token'):
            raise UserError(_("No refresh token available. Please authenticate with Zoho first."))
        
        data = {
            'refresh_token': config['refresh_token'],
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'grant_type': 'refresh_token'
        }
        
        try:
            response = self._make_http_request('POST', config['token_url'], data=data)
            token_data = response.json()
            
            access_token = token_data.get('access_token')
            if not access_token:
                raise UserError(_("Invalid response from Zoho token endpoint"))
            
            return access_token
            
        except Exception as e:
            _logger.error("Failed to get Zoho access token: %s", e)
            raise UserError(_("Unable to get Zoho access token: %s") % str(e))

    def get_workdrive_workspaces(self):
        """Récupère la liste des workspaces WorkDrive"""
        token = self._get_access_token()
        config = self._get_zoho_config()
        
        headers = {
            'Authorization': f'Zoho-oauthtoken {token}'
        }
        
        try:
            response = self._make_http_request(
                'GET',
                f"{config['workdrive_base_url']}/workdrive/api/v1/ws",
                headers=headers
            )
            return response.json()
        except Exception as e:
            _logger.error("Failed to get WorkDrive workspaces: %s", e)
            raise UserError(_("Unable to get WorkDrive workspaces: %s") % str(e))

    def create_workdrive_folder(self, folder_name, parent_id=None, workspace_id=None):
        """Crée un dossier dans WorkDrive"""
        token = self._get_access_token()
        config = self._get_zoho_config()
        
        if not workspace_id:
            workspaces = self.get_workdrive_workspaces()
            if not workspaces.get('data'):
                raise UserError(_("No WorkDrive workspaces found"))
            workspace_id = workspaces['data'][0]['id']
        
        headers = {
            'Authorization': f'Zoho-oauthtoken {token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "data": {
                "type": "folder",
                "attributes": {
                    "name": folder_name,
                    "parent_id": parent_id
                }
            }
        }
        
        try:
            response = self._make_http_request(
                'POST',
                f"{config['workdrive_base_url']}/workdrive/api/v1/ws/{workspace_id}/files",
                headers=headers,
                json=data
            )
            return response.json()
        except Exception as e:
            _logger.error("Failed to create WorkDrive folder: %s", e)
            raise UserError(_("Unable to create WorkDrive folder: %s") % str(e))

    def send_cliq_message(self, channel_unique_name, message):
        """Envoie un message dans un canal Cliq"""
        token = self._get_access_token()
        config = self._get_zoho_config()
        
        headers = {
            'Authorization': f'Zoho-oauthtoken {token}',
            'Content-Type': 'application/json'
        }
        
        data = {
            "text": message
        }
        
        try:
            response = self._make_http_request(
                'POST',
                f"{config['cliq_base_url']}/api/v2/channelsbyname/{channel_unique_name}/message",
                headers=headers,
                json=data
            )
            return response.json()
        except Exception as e:
            _logger.error("Failed to send Cliq message: %s", e)
            raise UserError(_("Unable to send Cliq message: %s") % str(e))

    def sync_project_to_workdrive(self, project_id):
        """Synchronise un projet vers Zoho WorkDrive"""
        project = self.env['project.project'].browse(project_id)
        
        try:
            folder_info = self.create_workdrive_folder(project.name)
            folder_id = folder_info.get('data', {}).get('id')
            
            if not folder_id:
                raise UserError(_("Invalid response from Zoho WorkDrive API"))
            
            project.write({
                'x_zoho_folder_id': folder_id,
                'x_sync_status': 'synced'
            })
            
            _logger.info("Project %s successfully synced to WorkDrive", project.name)
            return True
            
        except Exception as e:
            _logger.error("WorkDrive sync error for project %s: %s", project.name, e)
            project.write({'x_sync_status': 'error'})
            raise UserError(_("Failed to sync project to WorkDrive: %s") % str(e))

    def sync_task_to_cliq(self, task_id):
        """Synchronise une tâche vers Zoho Cliq"""
        task = self.env['project.task'].browse(task_id)
        project = task.project_id
        
        if not project.x_cliq_channel:
            _logger.warning(f"Pas de canal Cliq configuré pour le projet {project.name}")
            return False
        
        message = f"🎯 Nouvelle tâche: {task.name}\n"
        message += f"📊 Priorité: {task.x_priority_score or 'Non définie'}\n"
        message += f"⏰ Heures planifiées: {task.planned_hours}h\n"
        message += f"👤 Assigné à: {task.user_ids[0].name if task.user_ids else 'Non assigné'}"
        
        try:
            self.send_cliq_message(project.x_cliq_channel, message)
            task.write({'x_last_sync': fields.Datetime.now()})
            _logger.info("Task %s successfully synced to Cliq", task.name)
            return True
            
        except Exception as e:
            _logger.error("Cliq sync error for task %s: %s", task.name, e)
            raise UserError(_("Failed to sync task to Cliq: %s") % str(e))