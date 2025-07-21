# Zoho Odoo Sync Module

Module de synchronisation entre Odoo et la suite Zoho (Mail, Cliq, WorkDrive).

## Installation

1. Copiez le module `zoho_timesheet_sync` dans votre dossier `addons`
2. Redémarrez Odoo
3. Activez le mode développeur
4. Installez le module depuis Apps

## Configuration

### Paramètres Zoho API
Configurez les paramètres système suivants :
- `zoho.client_id` : ID client de votre app Zoho
- `zoho.client_secret` : Secret client de votre app Zoho  
- `zoho.refresh_token` : Token de rafraîchissement
- `zoho.base_url` : URL de base API (défaut: https://www.zohoapis.com)

### Projets
Dans chaque projet, configurez :
- **ID Dossier Zoho** : ID du dossier WorkDrive associé
- **Canal Cliq** : ID du canal Cliq pour les notifications

## Fonctionnalités

- ✅ Synchronisation des projets vers Zoho WorkDrive
- ✅ Notifications des tâches dans Zoho Cliq
- ✅ Champs de suivi de synchronisation
- ✅ Vue Kanban enrichie avec heures planifiées/consommées
- 🔄 Intégration N8N (à venir)

## Dépendances

- `hr_timesheet`
- `project`

## Version

Compatible Odoo 18.0