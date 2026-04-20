# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase


class TestBackupRejectWizard(TransactionCase):

    def test_wizard_creation(self):
        """L'assistant de rejet doit etre cree avec les bons champs."""
        req = self.env['backup.request'].create({
            'client_name': 'client_test',
            'config_id': self.env['backup.config'].create({
                'name': 'Test Config',
                'api_url': 'http://example.com',
                'api_key': 'key',
            }).id,
            'state': 'pending',
        })
        wizard = self.env['backup.reject.wizard'].create({
            'request_id': req.id,
            'rejection_reason': 'Donnees sensibles',
        })
        self.assertEqual(wizard.request_id, req)
        self.assertEqual(wizard.rejection_reason, 'Donnees sensibles')
