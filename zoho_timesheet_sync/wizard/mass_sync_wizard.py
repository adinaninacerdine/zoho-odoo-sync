from odoo import api, fields, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class MassSyncWizard(models.TransientModel):
    """Assistant pour synchroniser en masse les projets existants vers Zoho"""
    
    _name = 'zoho.mass.sync.wizard'
    _description = 'Assistant Synchronisation en Masse Zoho'
    
    project_ids = fields.Many2many(
        'project.project',
        string='Projets à synchroniser',
        help='Sélectionnez les projets à synchroniser avec Zoho'
    )
    
    sync_workdrive = fields.Boolean(
        string='Synchroniser WorkDrive',
        default=True,
        help='Créer des dossiers dans Zoho WorkDrive'
    )
    
    sync_cliq = fields.Boolean(
        string='Synchroniser Cliq', 
        default=True,
        help='Créer des canaux dans Zoho Cliq'
    )
    
    only_pending = fields.Boolean(
        string='Seulement les projets non synchronisés',
        default=True,
        help='Synchroniser uniquement les projets avec statut "pending" ou sans statut'
    )
    
    progress = fields.Text(
        string='Progression',
        readonly=True,
        help='Journal de progression de la synchronisation'
    )
    
    state = fields.Selection([
        ('draft', 'Configuration'),
        ('running', 'Synchronisation en cours'),
        ('done', 'Terminé')
    ], string='État', default='draft')
    
    success_count = fields.Integer(
        string='Projets synchronisés',
        readonly=True
    )
    
    error_count = fields.Integer(
        string='Erreurs',
        readonly=True
    )
    
    @api.model
    def default_get(self, fields_list):
        """Pré-sélectionne les projets selon le contexte"""
        res = super().default_get(fields_list)
        
        # Si appelé depuis une liste de projets, pré-sélectionner
        if self.env.context.get('active_model') == 'project.project':
            project_ids = self.env.context.get('active_ids', [])
            if project_ids:
                res['project_ids'] = [(6, 0, project_ids)]
        else:
            # Sinon, pré-sélectionner tous les projets non synchronisés
            pending_projects = self.env['project.project'].search([
                '|',
                ('x_sync_status', '=', 'pending'),
                ('x_sync_status', '=', False)
            ])
            res['project_ids'] = [(6, 0, pending_projects.ids)]
            
        return res
    
    def action_start_sync(self):
        """Lance la synchronisation en masse"""
        self.ensure_one()
        
        if not self.project_ids:
            raise UserError(_('Veuillez sélectionner au moins un projet à synchroniser'))
        
        # Vérifier la configuration Zoho
        config = self.env['ir.config_parameter'].sudo()
        if not all([
            config.get_param('zoho.client_id'),
            config.get_param('zoho.client_secret'),
            config.get_param('zoho.refresh_token')
        ]):
            raise UserError(_('Configuration Zoho incomplète. Veuillez vous authentifier d\'abord.'))
        
        self.write({
            'state': 'running',
            'progress': 'Début de la synchronisation...\n',
            'success_count': 0,
            'error_count': 0
        })
        
        # Traitement par lot pour éviter les timeouts
        zoho_service = self.env['zoho.api.service']
        
        progress_lines = ['Début de la synchronisation...']
        success_count = 0
        error_count = 0
        
        for project in self.project_ids:
            try:
                progress_lines.append(f"🔄 Synchronisation: {project.name}")
                
                # Filtrer selon les options
                if self.only_pending and project.x_sync_status == 'synced':
                    progress_lines.append(f"  ⏭️  Ignoré (déjà synchronisé)")
                    continue
                
                # Marquer comme en cours
                project.x_sync_status = 'pending'
                
                sync_success = False
                
                # Synchronisation WorkDrive
                if self.sync_workdrive:
                    try:
                        zoho_service.sync_project_to_workdrive(project.id)
                        progress_lines.append(f"  ✅ WorkDrive: Dossier créé")
                        sync_success = True
                    except Exception as e:
                        progress_lines.append(f"  ❌ WorkDrive: {str(e)[:100]}...")
                        _logger.error(f"WorkDrive sync failed for {project.name}: {e}")
                
                # Synchronisation Cliq (si WorkDrive réussi ou pas de WorkDrive)
                if self.sync_cliq and (sync_success or not self.sync_workdrive):
                    try:
                        # Note: sync_task_to_cliq nécessite une tâche, on peut créer une méthode dédiée
                        progress_lines.append(f"  ℹ️  Cliq: À implémenter (nécessite une tâche)")
                    except Exception as e:
                        progress_lines.append(f"  ❌ Cliq: {str(e)[:100]}...")
                        _logger.error(f"Cliq sync failed for {project.name}: {e}")
                
                # Mise à jour du statut final
                if sync_success:
                    project.x_sync_status = 'synced'
                    success_count += 1
                    progress_lines.append(f"  🎉 Projet synchronisé avec succès")
                    
                    # Message dans le chatter du projet
                    project.message_post(
                        body="✅ <b>Synchronisation Zoho réussie</b><br/>Projet synchronisé via l'assistant de masse",
                        message_type='notification'
                    )
                else:
                    project.x_sync_status = 'error'
                    error_count += 1
                    progress_lines.append(f"  ⚠️  Synchronisation échouée")
                    
            except Exception as e:
                error_count += 1
                project.x_sync_status = 'error'
                progress_lines.append(f"❌ ERREUR {project.name}: {str(e)[:100]}...")
                _logger.error(f"Mass sync error for project {project.name}: {e}")
                
                # Message d'erreur dans le chatter
                project.message_post(
                    body=f"❌ <b>Erreur synchronisation Zoho</b><br/>{str(e)}",
                    message_type='notification'
                )
        
        # Résumé final
        progress_lines.append(f"\n📊 RÉSUMÉ:")
        progress_lines.append(f"✅ Réussis: {success_count}")
        progress_lines.append(f"❌ Erreurs: {error_count}")
        progress_lines.append(f"📋 Total traité: {len(self.project_ids)}")
        
        self.write({
            'state': 'done',
            'progress': '\n'.join(progress_lines),
            'success_count': success_count,
            'error_count': error_count
        })
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'zoho.mass.sync.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': self.env.context
        }
    
    def action_close(self):
        """Ferme l'assistant"""
        return {'type': 'ir.actions.act_window_close'}
    
    def action_view_synced_projects(self):
        """Affiche les projets synchronisés"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Projets Synchronisés',
            'res_model': 'project.project',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.project_ids.ids), ('x_sync_status', '=', 'synced')],
            'context': {'create': False}
        }