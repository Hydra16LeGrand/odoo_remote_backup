# -*- coding: utf-8 -*-
{
    'name': "Remote Backup Management",
    'summary': "Request and download database backups from a remote backup API",
    'description': """
Remote Backup Management
========================

This module allows users to:
* Request database backups from a remote backup API
* Track backup request status (pending, validated, rejected)
* Download validated backups securely via token
* Manage backup API configurations

Current implementation relies on a generic REST backup API.
Planned migration to native Odoo.SH backup endpoints.
    """,
    'author': "Amara Baradji",
    'company': "Amara Baradji",
    'website': "https://amara-baradji.vercel.app/",
    'category': 'Tools',
    'version': '18.0.1.0.0',
    'depends': ['base', 'mail', 'odoo_db_remote_management'],
    'data': [
        'security/backup_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'data/ir_cron.xml',
        'views/backup_config_views.xml',
        'views/backup_request_views.xml',
        'views/menu_views.xml',
        'wizards/backup_download_wizard_views.xml',
    ],
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
