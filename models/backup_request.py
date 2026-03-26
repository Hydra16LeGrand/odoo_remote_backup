# -*- coding: utf-8 -*-

import logging
import requests
from dateutil import parser
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class BackupDownloadLog(models.Model):
    _name = 'backup.download.log'
    _description = 'Journal des Téléchargements'
    _order = 'create_date desc'

    request_id = fields.Many2one('backup.request', string="Demande", required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string="Téléchargé par", default=lambda self: self.env.user, readonly=True)
    download_date = fields.Datetime(string="Date", default=fields.Datetime.now, readonly=True)


class BackupRequest(models.Model):
    _name = 'backup.request'
    _description = 'Demande de Sauvegarde'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'
    _rec_name = 'name'

    name = fields.Char(
        string="Référence",
        default=lambda self: _('Nouveau'),
        copy=False,
        readonly=True,
        tracking=True
    )

    active = fields.Boolean(default=True)

    # Informations de la Demande
    client_name = fields.Selection(
        selection='_get_available_clients',
        string="Nom du Client",
        required=True,
        help="Base de données client à sauvegarder"
    )
    anonymize = fields.Boolean(
        string="Anonymiser les données",
        default=True,
        help="Anonymiser les données sensibles (recommandé pour le développement local)"
    )
    include_filestore = fields.Boolean(
        string="Inclure le Filestore",
        default=False,
        help="Inclure les fichiers/images (augmente considérablement la taille de la sauvegarde)"
    )

    # Statut
    state = fields.Selection(
        [
            ('draft', 'Brouillon'),
            ('pending', 'En attente de validation'),
            ('validated', 'Validé'),
            ('rejected', 'Rejeté'),
            ('downloaded', 'Téléchargé'),
            ('cancelled', 'Annulé')
        ],
        string="Statut",
        default='draft',
        required=True,
        tracking=True
    )

    # Intégration API
    api_request_id = fields.Integer(
        string="ID Requête API",
        readonly=True,
        help="ID de la demande sur l'API distante"
    )

    # Dates et Utilisateurs
    request_date = fields.Datetime(
        string="Date de demande",
        readonly=True
    )
    requested_by = fields.Many2one(
        'res.users',
        string="Demandé par",
        default=lambda self: self.env.user,
        readonly=True,
        required=True
    )
    validated_date = fields.Datetime(
        string="Date de validation",
        readonly=True
    )
    validated_by_name = fields.Char(
        string="ID Validateur",
        readonly=True,
        help="ID du validateur (provenant de l'API)"
    )

    # Rejet
    rejection_reason = fields.Text(
        string="Motif de rejet",
        readonly=True
    )
    rejected_date = fields.Datetime(
        string="Date de rejet",
        readonly=True
    )

    # Téléchargement
    download_url = fields.Char(
        string="URL de téléchargement",
        compute='_compute_download_url',
        help="URL pour télécharger la sauvegarde"
    )
    file_size_estimate = fields.Char(
        string="Taille estimée",
        compute='_compute_file_size_estimate',
        help="Taille estimée du fichier selon les options"
    )
    downloaded_date = fields.Datetime(
        string="Date de téléchargement",
        readonly=True
    )
    
    # Journal des téléchargements
    download_log_ids = fields.One2many(
        'backup.download.log',
        'request_id',
        string="Journal des téléchargements"
    )
    
    download_count = fields.Integer(
        string="Nombre de téléchargements",
        compute='_compute_download_count',
        store=True
    )

    # Configuration
    config_id = fields.Many2one(
        'backup.config',
        string="Configuration API",
        required=True,
        default=lambda self: self._get_default_config()
    )

    # Contraintes
    _sql_constraints = [
        ('api_request_id_unique', 'unique(api_request_id)',
         "L'ID de la demande API doit être unique"),
    ]
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self._generate_sequence_name()
        return super().create(vals_list)

    def _generate_sequence_name(self):
        return self.env['ir.sequence'].next_by_code('backup.request') or _('Nouveau')

    @api.depends('download_log_ids')
    def _compute_download_count(self):
        for record in self:
            record.download_count = len(record.download_log_ids)

    def _get_default_config(self):
        """Récupérer la configuration active par défaut"""
        config = self.env['backup.config'].search([('active', '=', True)], limit=1)
        return config.id if config else False

    @api.model
    def _get_available_clients(self):
        """Obtenir la liste des clients disponibles depuis le cache ou l'API"""
        # Essayer d'abord depuis le cache
        cached_clients = self.env['ir.config_parameter'].sudo().get_param(
            'backup.available_clients', ''
        )

        if cached_clients:
            clients = cached_clients.split(',')
            return [(client, client) for client in clients if client]

        # Si pas de cache, essayer de récupérer depuis l'API
        config = self.env['backup.config'].search([('active', '=', True)], limit=1)
        if config:
            try:
                url = f"{config.api_url.rstrip('/')}/backups/clients"
                response = requests.get(url, headers=config._get_headers(), timeout=10)
                response.raise_for_status()
                clients = response.json()

                # Mettre en cache le résultat
                self.env['ir.config_parameter'].sudo().set_param(
                    'backup.available_clients',
                    ','.join(clients)
                )

                return [(client, client) for client in clients]
            except Exception as e:
                _logger.warning(f"Échec de la récupération des clients depuis l'API : {str(e)}")

        return []

    @api.depends('config_id', 'api_request_id', 'state')
    def _compute_download_url(self):
        """Calculer l'URL de téléchargement (sera générée dynamiquement)"""
        for record in self:
            if record.api_request_id and record.state == 'validated' and record.config_id:
                record.download_url = f"{record.config_id.api_url.rstrip('/')}/backups/download/{record.api_request_id}"
            else:
                record.download_url = False

    @api.depends('include_filestore')
    def _compute_file_size_estimate(self):
        """Estimer la taille du fichier selon les options"""
        for record in self:
            if record.include_filestore:
                record.file_size_estimate = "~500 MB"
            else:
                record.file_size_estimate = "~5 MB"

    def _parse_api_date(self, date_str):
        """Analyser la chaîne de date de l'API vers un datetime Odoo"""
        if not date_str:
            return False
        try:
            # Analyser le format ISO 8601 (ex: 2026-02-16T16:50:08.261180Z)
            dt = parser.parse(date_str)
            # Convertir en datetime naïf UTC pour Odoo
            return fields.Datetime.to_string(dt.astimezone(None).replace(tzinfo=None))
        except (ValueError, TypeError):
            _logger.warning(f"Échec de l'analyse de la date : {date_str}")
            return False

    def action_send_request(self):
        """Envoyer la demande de sauvegarde à l'API"""
        self.ensure_one()

        if not self.config_id:
            raise UserError(_("Veuillez d'abord configurer une API de sauvegarde"))

        if self.state != 'draft':
            raise UserError(_("Seules les demandes brouillon peuvent être envoyées"))

        try:
            url = f"{self.config_id.api_url.rstrip('/')}/requests"
            payload = {
                'client_name': self.client_name,
                'anonymize': self.anonymize,
                'include_filestore': self.include_filestore,
            }

            response = requests.post(
                url,
                json=payload,
                headers=self.config_id._get_headers(),
                timeout=10
            )
            response.raise_for_status()

            result = response.json()

            # Mettre à jour l'enregistrement avec la réponse de l'API
            self.write({
                'api_request_id': result.get('id'),
                'state': 'pending',
                'request_date': fields.Datetime.now(),
            })

            # Forcer le rechargement
            return {
                'type': 'ir.actions.client',
                'tag': 'reload', 
            }

        except requests.exceptions.RequestException as e:
            error_msg = self._format_api_error(e)
            raise UserError(_("Échec de l'envoi de la demande : %s") % error_msg)

    def action_refresh_status(self):
        """Rafraîchir le statut de la demande depuis l'API"""
        self.ensure_one()

        if not self.api_request_id:
            raise UserError(_("Aucun ID de demande API trouvé"))

        try:
            url = f"{self.config_id.api_url.rstrip('/')}/requests/{self.api_request_id}"
            _logger.info(f"Rafraîchissement statut pour Demande {self.id} (API ID: {self.api_request_id}) - URL: {url}")
            
            response = requests.get(
                url,
                headers=self.config_id._get_headers(),
                timeout=10
            )
            response.raise_for_status()

            result = response.json()
            self._update_from_api_data(result)

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

        except requests.exceptions.RequestException as e:
            _logger.error(f"Échec du rafraîchissement pour la Demande {self.id}: {str(e)}")
            error_msg = self._format_api_error(e)
            raise UserError(_("Échec du rafraîchissement du statut (ID: %s) : %s") % (self.api_request_id, error_msg))

    def action_validate(self):
        """Valider la demande de sauvegarde (validateur uniquement)"""
        self.ensure_one()

        if not self.api_request_id:
            raise UserError(_("Aucun ID de demande API trouvé"))

        if self.state != 'pending':
            raise UserError(_("Seules les demandes en attente peuvent être validées"))

        try:
            url = f"{self.config_id.api_url.rstrip('/')}/requests/{self.api_request_id}/validate"
            response = requests.patch(
                url,
                headers=self.config_id._get_headers(),
                timeout=10
            )
            response.raise_for_status()

            result = response.json()
            self._update_from_api_data(result)

            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }

        except requests.exceptions.RequestException as e:
            # Gérer le cas où la demande est déjà validée sur le serveur
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 422:
                try:
                    error_detail = e.response.json()
                    detail_msg = str(error_detail.get('detail', '')).lower()
                    if 'validated' in detail_msg:
                        # Conflit : Déjà validé. Rafraîchir le statut à la place.
                        _logger.info(f"Demande {self.api_request_id} déjà validée sur l'API. Rafraîchissement du statut.")
                        return self.action_refresh_status()
                except Exception:
                    pass  # Repli vers la gestion d'erreur normale

            error_msg = self._format_api_error(e)
            raise UserError(_("Échec de la validation de la demande : %s") % error_msg)

    def action_reject(self):
        """Ouvrir l'assistant pour rejeter la demande avec un motif"""
        self.ensure_one()

        if self.state != 'pending':
            raise UserError(_("Seules les demandes en attente peuvent être rejetées"))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Rejeter la demande de sauvegarde'),
            'res_model': 'backup.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_view_downloads(self):
        """Voir la liste des téléchargements"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Téléchargements'),
            'res_model': 'backup.download.log',
            'view_mode': 'list,form',
            'domain': [('request_id', '=', self.id)],
            'context': {'default_request_id': self.id},
        }

    def action_download(self):
        """Télécharger la sauvegarde via un jeton temporaire"""
        self.ensure_one()

        if self.state not in ['validated', 'downloaded']:
            raise UserError(_("Seules les demandes validées peuvent être téléchargées"))

        if not self.api_request_id:
            raise UserError(_("Aucun ID de demande API trouvé"))

        try:
            # Générer un jeton de téléchargement temporaire
            url = f"{self.config_id.api_url.rstrip('/')}/backups/download/{self.api_request_id}/generate_token"
            response = requests.post(
                url,
                headers=self.config_id._get_headers(),
                timeout=10
            )
            response.raise_for_status()

            token_data = response.json()

            # Créer un journal de téléchargement
            self.env['backup.download.log'].create({
                'request_id': self.id,
            })

            # Mettre à jour le statut
            if self.state != 'downloaded':
                self.state = 'downloaded'

            # Ouvrir l'URL de téléchargement
            download_url = token_data.get('download_url')
            
            # Correction pour les URL locales ou relatives
            if download_url:
                if not download_url.startswith(('http://', 'https://')):
                    base_url = self.config_id.api_url.rstrip('/')
                    if not download_url.startswith('/'):
                        download_url = '/' + download_url
                    download_url = base_url + download_url
                elif 'localhost' in download_url and 'localhost' not in self.config_id.api_url:
                    path = download_url.split('download/public/', 1)[-1]
                    base_url = self.config_id.api_url.rstrip('/')
                    download_url = f"{base_url}/backups/download/public/{path}"

            _logger.info(f"Ouverture de l'URL de téléchargement : {download_url}")

            return {
                'type': 'ir.actions.act_url',
                'url': download_url,
                'target': 'new',
            }

        except requests.exceptions.RequestException as e:
            error_msg = self._format_api_error(e)
            raise UserError(_("Échec de la génération du lien de téléchargement : %s") % error_msg)

    def action_cancel(self):
        """Annuler la demande"""
        self.ensure_one()
        if self.state in ['validated', 'downloaded']:
            raise UserError(_("Impossible d'annuler des demandes validées ou téléchargées"))

        self.state = 'cancelled'

    def _update_from_api_data(self, data):
        """Mettre à jour l'enregistrement depuis les données de l'API"""
        vals = {}

        # Mappage du statut API vers l'état interne
        api_status = data.get('status')
        if api_status == 'pending':
            vals['state'] = 'pending'
        elif api_status == 'validated':
            vals['state'] = 'validated'
            vals['validated_date'] = self._parse_api_date(data.get('validated_at'))
            vals['validated_by_name'] = data.get('validated_by')
        elif api_status == 'rejected':
            vals['state'] = 'rejected'
            vals['rejection_reason'] = data.get('rejection_reason')
            vals['rejected_date'] = self._parse_api_date(data.get('rejected_at'))
        elif api_status == 'downloaded':
            vals['state'] = 'downloaded'

        if vals:
            self.write(vals)

    def _format_api_error(self, exception):
        """Formater le message d'erreur API"""
        if hasattr(exception, 'response') and exception.response is not None:
            try:
                error_detail = exception.response.json()
                return f"{exception.response.status_code}: {error_detail.get('detail', str(exception))}"
            except:
                return f"{exception.response.status_code}: {exception.response.text}"
        return str(exception)

    @api.model
    def cron_sync_pending_requests(self):
        """Tâche cron pour synchroniser les demandes en attente"""
        pending_requests = self.search([('state', '=', 'pending')])

        for request in pending_requests:
            try:
                request.action_refresh_status()
            except Exception as e:
                _logger.error(f"Échec de la synchro de la demande {request.id}: {str(e)}")
                continue
