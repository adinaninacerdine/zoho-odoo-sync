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
            redirect_uri = request.env['ir.config_parameter'].get_param('web.base.url')
            
            oauth_params = {
                'scope': 'WorkDrive.files.ALL,ZohoCliq.Channels.ALL',
                'client_id': client_id,
                'response_type': 'code',
                'redirect_uri': redirect_uri,
                'access_type': 'offline'
            }
            
            # Récupérer le domaine Zoho depuis la configuration (défaut: .com)
            zoho_domain = config.get_param('zoho.domain', 'com')
            auth_url = f"https://accounts.zoho.{zoho_domain}/oauth/v2/auth?{urlencode(oauth_params)}"
            
            _logger.info("Redirecting to Zoho OAuth: %s", auth_url)
            
            # Template de redirection HTML
            return request.render('zoho_timesheet_sync.auth_redirect_template', {
                'auth_url': auth_url,
                'title': 'Redirection vers Zoho'
            })
            
        except Exception as e:
            _logger.error("Auth start error: %s", e)
            return self._render_error(f"Erreur d'authentification: {str(e)}")
    
    @http.route(['/auth/zoho/callback', '/zoho/auth/callback'], type='http', auth='public', methods=['GET', 'POST'])  
    def auth_callback(self, **kwargs):
        """Callback après authentification Zoho"""
        
        # Debug: Log tous les paramètres reçus avec plus de détails
        _logger.info("=== ZOHO OAUTH CALLBACK DEBUG ===")
        _logger.info("Full request data: %s", dict(request.httprequest.args))
        _logger.info("Callback kwargs: %s", kwargs)
        _logger.info("Request method: %s", request.httprequest.method)
        _logger.info("Request URL: %s", request.httprequest.url)
        
        # Traiter les paramètres selon la documentation Zoho OAuth
        code = kwargs.get('code')
        error = kwargs.get('error')
        error_description = kwargs.get('error_description', '')
        location = kwargs.get('location')
        accounts_server = kwargs.get('accounts-server')
        
        # Gestion des erreurs OAuth
        if error:
            if error == 'access_denied':
                _logger.warning("User denied Zoho OAuth authorization")
                return self._render_error("Autorisation refusée par l'utilisateur")
            else:
                _logger.error("Zoho OAuth error: %s - %s", error, error_description)
                return self._render_error(f"Erreur Zoho: {error} - {error_description}")
        
        # Vérification du code d'autorisation
        if not code:
            _logger.error("No authorization code received. Full callback data: %s", kwargs)
            return self._render_error(f"Code d'autorisation manquant. Paramètres reçus: {list(kwargs.keys())}")
        
        # Log des paramètres additionnels Zoho
        if location:
            _logger.info("Zoho location parameter: %s", location)
        if accounts_server:
            _logger.info("Zoho accounts-server parameter: %s", accounts_server)
        
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
            'redirect_uri': config.get_param('web.base.url'),
            'code': code
        }
        
        try:
            # Utiliser le même domaine pour le token
            zoho_domain = config.get_param('zoho.domain', 'com')
            zoho_domain = config.get_param('zoho.domain', 'com')
            token_url = f"https://accounts.zoho.{zoho_domain}/oauth/v2/token"
            
            response = requests.post(
                token_url,
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