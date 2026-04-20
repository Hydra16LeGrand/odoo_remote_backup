# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError


class TestBackupRequest(TransactionCase):

    def test_sequence_generation(self):
        """La reference doit suivre le format BR-AA-NNN."""
        req = self.env['backup.request'].create({
            'client_name': 'client_test',
            'config_id': self.env['backup.config'].create({
                'name': 'Test Config',
                'api_url': 'http://example.com',
                'api_key': 'key',
            }).id,
        })
        self.assertTrue(req.name)
        self.assertRegex(req.name, r'^BR-\d{2}-\d{3}$')

    def test_state_transition_cancel(self):
        """Une demande brouillon peut etre annulee, une valide non."""
        req = self.env['backup.request'].create({
            'client_name': 'client_test',
            'config_id': self.env['backup.config'].create({
                'name': 'Test Config 2',
                'api_url': 'http://example.com',
                'api_key': 'key',
            }).id,
        })
        self.assertEqual(req.state, 'draft')
        req.state = 'cancelled'
        self.assertEqual(req.state, 'cancelled')

        validated = self.env['backup.request'].create({
            'client_name': 'client_test',
            'config_id': self.env['backup.config'].create({
                'name': 'Test Config 3',
                'api_url': 'http://example.com',
                'api_key': 'key',
            }).id,
            'state': 'validated',
        })
        with self.assertRaises(UserError):
            validated.action_cancel()

    def test_download_log_count(self):
        """Le nombre de telechargements doit etre calcule."""
        req = self.env['backup.request'].create({
            'client_name': 'client_test',
            'config_id': self.env['backup.config'].create({
                'name': 'Test Config 4',
                'api_url': 'http://example.com',
                'api_key': 'key',
            }).id,
        })
        self.env['backup.download.log'].create({'request_id': req.id})
        self.env['backup.download.log'].create({'request_id': req.id})
        self.assertEqual(req.download_count, 2)
