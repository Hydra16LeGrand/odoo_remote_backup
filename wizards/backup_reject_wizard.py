# -*- coding: utf-8 -*-

import logging
import requests
from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class BackupRejectWizard(models.TransientModel):
    _name = 'backup.reject.wizard'
    _description = 'Reject Backup Request Wizard'

    request_id = fields.Many2one(
        'backup.request',
        string="Backup Request",
        required=True,
        readonly=True
    )
    rejection_reason = fields.Text(
        string="Rejection Reason",
        required=True,
        help="Explain why this backup request is being rejected"
    )

    def action_confirm_reject(self):
        """Confirm rejection and send to API"""
        self.ensure_one()

        if not self.request_id.api_request_id:
            raise UserError(_("No API request ID found"))

        try:
            url = f"{self.request_id.config_id.api_url.rstrip('/')}/requests/{self.request_id.api_request_id}/reject"
            payload = {'reason': self.rejection_reason}

            response = requests.patch(
                url,
                json=payload,
                headers=self.request_id.config_id._get_headers(),
                timeout=10
            )
            response.raise_for_status()

            result = response.json()

            # Update request with rejection info
            self.request_id.write({
                'state': 'rejected',
                'rejection_reason': self.rejection_reason,
                'rejected_date': fields.Datetime.now(),
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _("Request Rejected"),
                    'message': _("Backup request has been rejected"),
                    'sticky': False,
                    'type': 'warning',
                }
            }

        except requests.exceptions.RequestException as e:
            error_msg = self.request_id._format_api_error(e)
            raise UserError(_("Failed to reject request: %s") % error_msg)
