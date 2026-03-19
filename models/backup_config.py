# -*- coding: utf-8 -*-

import logging
import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BackupConfig(models.Model):
    _name = 'backup.config'
    _description = 'Configuration API de Sauvegarde'
    _order = 'name'

    name = fields.Char(
        string="Nom de la configuration",
        required=True,
        help="Nom de cette configuration (ex: 'Production Backup API')"
    )
    api_url = fields.Char(
        string="URL de base de l'API",
        required=True,
        default="http://your-backup-api.example.com:8000",
        help="URL de base de l'API de backup (ex: http://api.example.com:8000)"
    )
    api_key = fields.Char(
        string="Clé API",
        required=True,
        help="Clé d'API pour l'authentification (header X-API-Key)"
    )
    role = fields.Selection(
        [
            ('dev', 'Développeur'),
            ('validator', 'Validateur')
        ],
        string="Rôle API",
        required=True,
        default='dev',
        help="Rôle de l'utilisateur sur l'API de backup"
    )
    active = fields.Boolean(default=True)

    # Connection test fields
    api_user_info = fields.Text(
        string="Infos utilisateur API",
        readonly=True,
        help="Informations de l'utilisateur API (depuis /auth/me)"
    )
    last_connection_test = fields.Datetime(
        string="Dernier test de connexion",
        readonly=True
    )
    connection_status = fields.Selection(
        [
            ('success', 'Connecté'),
            ('failed', 'Échoué'),
            ('never', 'Jamais testé')
        ],
        string="Statut de connexion",
        default='never',
        readonly=True
    )
    connection_error = fields.Text(
        string="Dernière erreur",
        readonly=True
    )

    available_clients_display = fields.Text(
        string="Clients disponibles",
        readonly=True,
        help="Liste des clients disponibles récupérée depuis l'API"
    )

    # Constraints
    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'Le nom de la configuration doit être unique.'),
    ]

    def _get_headers(self):
        """Retourner les en-têtes HTTP pour les requêtes API"""
        self.ensure_one()
        return {
            'X-API-Key': self.api_key,
            'Content-Type': 'application/json',
        }

    def test_connection(self):
        """Tester la connexion à l'API de sauvegarde en appelant /auth/me"""
        self.ensure_one()

        try:
            url = f"{self.api_url.rstrip('/')}/auth/me"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()
 
            user_info = response.json()

            # Update connection status
            self.write({
                'connection_status': 'success',
                'api_user_info': str(user_info),
                'last_connection_test': fields.Datetime.now(),
                'connection_error': False,
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Connexion Réussie"),
                    'message': _("Connecté en tant que : %(username)s (Rôle : %(role)s)") % {
                        'username': user_info.get('username', 'Inconnu'),
                        'role': user_info.get('role', 'Inconnu'),
                    },
                    'sticky': False,
                    'type': 'success',
                }
            }

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"{e.response.status_code}: {error_detail.get('detail', str(e))}"
                except:
                    error_msg = f"{e.response.status_code}: {e.response.text}"

            self.write({
                'connection_status': 'failed',
                'last_connection_test': fields.Datetime.now(),
                'connection_error': error_msg,
            })

            raise UserError(_("La connexion a échoué : %s") % error_msg)

    def action_refresh_clients(self):
        """Actualiser la liste des clients disponibles depuis l'API"""
        self.ensure_one()

        try:
            url = f"{self.api_url.rstrip('/')}/backups/clients"
            response = requests.get(url, headers=self._get_headers(), timeout=10)
            response.raise_for_status()

            clients = response.json()

            # Store in ir.config_parameter for caching
            self.env['ir.config_parameter'].sudo().set_param(
                'backup.available_clients',
                ','.join(clients)
            )
            
            # Use newline for display field
            self.write({
                'available_clients_display': '\n'.join(clients)
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Clients actualisés"),
                    'message': _("%d clients disponibles trouvés") % len(clients),
                    'sticky': False,
                    'type': 'success',
                }
            }

        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    error_msg = f"{error_detail.get('detail', str(e))}"
                except:
                    error_msg = e.response.text

            raise UserError(_("Échec de l'actualisation des clients : %s") % error_msg)
