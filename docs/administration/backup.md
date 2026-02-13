# Backup & Restore

Protect your directory and application data with regular backups.

---

## What to Back Up

| Data Store | Contains | Method |
|---|---|---|
| **OpenLDAP** | All identity data (users, groups, systems, DNS, DHCP, sudo) | `slapcat` (LDIF export) |
| **PostgreSQL** | Audit logs, settings, templates, sessions | `pg_dump` |
| **Configuration** | `.env`, TLS certificates, custom schemas | File copy |

!!! tip
    Redis does not need to be backed up — it contains only ephemeral cache and session data.

---

## Manual Backup

### LDAP

Export the entire directory to an LDIF file:

```bash
docker compose exec ldap slapcat > backup-$(date +%Y%m%d).ldif
```

### PostgreSQL

```bash
docker compose exec postgres pg_dump -U heracles heracles > backup-$(date +%Y%m%d).sql
```

### Configuration

```bash
cp .env .env.backup
cp -r pki/ pki-backup/
```

---

## Automated Backup (Ansible)

Use the provided Ansible playbook for scheduled backups:

```bash
ansible-playbook -i inventory/production.yml playbooks/backup.yml
```

This creates timestamped backups of both LDAP and PostgreSQL with configurable retention.

---

## Restore

### LDAP

!!! danger "Destructive Operation"
    Restoring LDAP data will overwrite the current directory. Stop the API before restoring.

```bash
# Stop the API
docker compose stop api

# Clear and restore LDAP
docker compose exec ldap slapadd -l /path/to/backup.ldif

# Restart
docker compose up -d
```

### PostgreSQL

```bash
docker compose exec -T postgres psql -U heracles heracles < backup.sql
```

---

## Backup Schedule Recommendations

| Environment | Frequency | Retention |
|---|---|---|
| Production | Daily (LDAP + PostgreSQL) | 30 days |
| Staging | Weekly | 7 days |
| Development | Before major changes | Manual |
