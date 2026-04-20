# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


class TestBackupConfig(TransactionCase):

    def test_default_config(self):
        """La configuration par defaut doit etre la premiere active."""
        config = self.env['backup.config'].create({
            'name': 'Default Test',
            'api_url': 'http://example.com',
            'api_key': 'key',
        })
        default = self.env['backup.request']._get_default_config()
        self.assertEqual(default, config.id)

    def test_sql_constraint_name_unique(self):
        """Le nom de configuration doit etre unique."""
        self.env['backup.config'].create({
            'name': 'UniqueName',
            'api_url': 'http://a.com',
            'api_key': 'k',
        })
        with self.assertRaises(ValidationError):
            self.env['backup.config'].create({
                'name': 'UniqueName',
                'api_url': 'http://b.com',
                'api_key': 'k2',
            })
