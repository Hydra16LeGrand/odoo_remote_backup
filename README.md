# Odoo Remote Backup

**[Français](#francais) | [English](#english)**

---

<a name="francais"></a>
## Français

### Résumé

Ce module fournit un workflow complet pour demander, valider et télécharger des sauvegardes de bases de données clientes depuis la base interne (Hub). Il inclut une validation à deux niveaux, un téléchargement sécurisé par jeton, et des options d'anonymisation pour protéger les données sensibles.

### Fonctionnalités

- **Workflow de demande** : cycle de vie Brouillon -> En attente -> Validé -> Téléchargé / Rejeté
- **Validation à deux niveaux** : un développeur crée la demande, un validateur l'approuve ou la rejette avec motif
- **Téléchargement sécurisé** : génération d'un jeton temporaire pour le téléchargement du fichier
- **Anonymisation** : option pour anonymiser les données sensibles avant la sauvegarde (utile pour le développement)
- **Exclusion du filestore** : option pour exclure les fichiers joints et alléger la sauvegarde
- **Journal des téléchargements** : traçabilité de chaque téléchargement (utilisateur, date, heure)
- **Synchronisation automatique** : mise à jour du statut toutes les 5 minutes via cron
- **Intégration Instance Hub** : menu intégré sous le module `odoo_db_remote_management`
- **Numérotation automatique** : références uniques au format `BR-AA-NNN`

### Installation

1. Installer d'abord le module `odoo_db_remote_management` (requis pour la structure de menu).
2. Placer ce module dans le répertoire `addons`.
3. Mettre à jour la liste des applications et installer `Remote Backup Management`.

### Configuration

1. Naviguer vers **Instance Hub > Configuration > Sauvegardes API**.
2. Créer une configuration avec l'URL de l'API et la clé d'authentification.
3. Tester la connexion et actualiser la liste des clients disponibles.
4. Assigner les groupes utilisateurs (Backup User, Validator, Manager) via **Paramètres > Utilisateurs**.

### Note sur Odoo.SH

L'implémentation actuelle s'appuie sur une API REST générique de gestion de sauvegardes. Une évolution prévue consiste à interconnecter ce module directement avec les endpoints natifs de sauvegarde d'Odoo.SH pour éliminer la dépendance à une API externe, et ainsi centraliser la gestion des backups sans infrastructure supplémentaire.

### Sécurité

Trois niveaux d'accès sont définis :

- **Backup User (Developer)** : peut créer et télécharger ses propres demandes
- **Backup Validator** : peut valider ou rejeter toutes les demandes
- **Backup Manager** : accès complet incluant la configuration API

### Dépendances

- [odoo_db_remote_management](https://github.com/Hydra16LeGrand/odoo_db_remote_management) : fournit la structure de menu Instance Hub

---

<a name="english"></a>
## English

### Summary

This module provides a complete workflow to request, validate and download client database backups from the internal Hub database. It includes two-level approval, secure token-based download, and anonymization options to protect sensitive data.

### Features

- **Request workflow**: lifecycle Draft -> Pending -> Validated -> Downloaded / Rejected
- **Two-level approval**: a developer creates the request, a validator approves or rejects it with a reason
- **Secure download**: temporary token generation for file download
- **Anonymization**: option to anonymize sensitive data before backup (useful for development)
- **Filestore exclusion**: option to exclude attachments and lighten the backup
- **Download logs**: audit trail for every download (user, date, time)
- **Automatic sync**: status refresh every 5 minutes via cron
- **Instance Hub integration**: menu integrated under the `odoo_db_remote_management` module
- **Automatic numbering**: unique references in `BR-YY-NNN` format

### Installation

1. First install the `odoo_db_remote_management` module (required for the menu structure).
2. Place this module in the `addons` directory.
3. Update the app list and install `Remote Backup Management`.

### Configuration

1. Navigate to **Instance Hub > Configuration > Backup APIs**.
2. Create a configuration with the API URL and authentication key.
3. Test the connection and refresh the list of available clients.
4. Assign user groups (Backup User, Validator, Manager) via **Settings > Users**.

### Odoo.SH Note

The current implementation relies on a generic REST backup management API. A planned evolution is to connect this module directly to Odoo.SH native backup endpoints, removing the dependency on an external API and centralizing backup management without additional infrastructure.

### Security

Three access levels are defined:

- **Backup User (Developer)**: can create and download their own requests
- **Backup Validator**: can validate or reject all requests
- **Backup Manager**: full access including API configuration

### Dependencies

- [odoo_db_remote_management](https://github.com/Hydra16LeGrand/odoo_db_remote_management): provides the Instance Hub menu structure

---

## License

LGPL-3

## Author

Amara Baradji
