import json
import logging
import requests
from urllib.parse import urlencode
from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ZohoAuthController(http.Controller):
    """Controller pour l'authentification OAuth Zoho"""
    
    @http.route('/zoho/auth/start', type='http', auth='user', methods=['GET'])
    def start_auth(self, **kwargs):
        """Démarre le processus d'authentification OAuth"""
        try:
            # Récupérer les paramètres Zoho
            config = request.env['ir.config_parameter'].sudo()
            client_id = config.get_param('zoho.client_id')
            
            if not client_id:
                return self._render_error("Configuration Zoho manquante. Veuillez configurer zoho.client_id")
            
            # Paramètres OAuth
            redirect_uri = f"{request.env['ir.config_parameter'].get_param('web.base.url')}/zoho/auth/callback"
            
            oauth_params = {
                'scope': 'ZohoWorkDrive.files.read,ZohoWorkDrive.files.create',
                'client_id': client_id,
                'response_type': 'code',
                'redirect_uri': redirect_uri,
                'access_type': 'offline'
            }
            
            auth_url = f"https://accounts.zoho.com/oauth/v2/auth?{urlencode(oauth_params)}"
            
            _logger.info("Redirecting to Zoho OAuth: %s", auth_url)
            
            # Template de redirection HTML
            return request.render('zoho_timesheet_sync.auth_redirect_template', {
                'auth_url': auth_url,
                'title': 'Redirection vers Zoho'
            })
            
        except Exception as e:
            _logger.error("Auth start error: %s", e)
            return self._render_error(f"Erreur d'authentification: {str(e)}")
    
    @http.route('/zoho/auth/callback', type='http', auth='public', methods=['GET', 'POST'])  
    def auth_callback(self, **kwargs):
        """Callback après authentification Zoho"""
        
        # Debug: Log tous les paramètres reçus
        _logger.info("Callback parameters received: %s", kwargs)
        
        code = kwargs.get('code')
        error = kwargs.get('error')
        error_description = kwargs.get('error_description', '')
        
        if error:
            _logger.error("Zoho OAuth error: %s - %s", error, error_description)
            return self._render_error(f"Erreur Zoho: {error} - {error_description}")
        
        if not code:
            _logger.error("No authorization code received. Full callback data: %s", kwargs)
            return self._render_error(f"Code d'autorisation manquant. Paramètres reçus: {list(kwargs.keys())}")
        
        try:
            # Échanger le code contre un refresh token
            refresh_token = self._exchange_code_for_token(code)
            
            if refresh_token:
                # Sauvegarder le refresh token
                request.env['ir.config_parameter'].sudo().set_param('zoho.refresh_token', refresh_token)
                
                _logger.info("Refresh token successfully obtained and saved")
                
                return self._render_success("Authentification Zoho réussie ! Le refresh token a été sauvegardé.")
            else:
                return self._render_error("Impossible d'obtenir le refresh token")
                
        except Exception as e:
            _logger.error("Auth callback error: %s", e)
            return self._render_error(f"Erreur lors de l'échange du token: {str(e)}")
    
    def _exchange_code_for_token(self, code):
        """Échange le code d'autorisation contre un refresh token"""
        config = request.env['ir.config_parameter'].sudo()
        
        data = {
            'grant_type': 'authorization_code',
            'client_id': config.get_param('zoho.client_id'),
            'client_secret': config.get_param('zoho.client_secret'),
            'redirect_uri': f"{config.get_param('web.base.url')}/zoho/auth/callback",
            'code': code
        }
        
        try:
            response = requests.post(
                'https://accounts.zoho.com/oauth/v2/token',
                data=data,
                timeout=30
            )
            
            _logger.info("Token exchange response status: %s", response.status_code)
            _logger.info("Token exchange response: %s", response.text)
            
            if response.status_code == 200:
                token_data = response.json()
                refresh_token = token_data.get('refresh_token')
                
                if refresh_token:
                    return refresh_token
                else:
                    _logger.error("No refresh token in response: %s", token_data)
                    return None
            else:
                _logger.error("Token exchange failed: %s - %s", response.status_code, response.text)
                return None
                
        except Exception as e:
            _logger.error("Token exchange exception: %s", e)
            raise
    
    def _render_success(self, message):
        """Affiche une page de succès"""
        return request.render('zoho_timesheet_sync.auth_success_template', {
            'message': message,
            'title': 'Authentification Zoho Réussie'
        })
    
    def _render_error(self, message):
        """Affiche une page d'erreur"""  
        return request.render('zoho_timesheet_sync.auth_error_template', {
            'error': message,
            'title': 'Erreur Authentification Zoho'
        })