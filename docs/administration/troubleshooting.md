# Troubleshooting

Common issues and how to resolve them.

---

## Diagnostic Commands

Start by gathering information:

```bash
# Check container status
docker compose ps

# View all logs
make logs

# View specific service logs
make logs s=api
make logs s=ldap
make logs s=ui

# Shell into a container
make shell s=api
```

---

## Common Issues

### Services Won't Start

**Symptoms:** Containers exit immediately or restart loop.

**Steps:**

1. Check logs: `make logs`
2. Check disk space: `df -h`
3. Check ports: `ss -tlnp | grep -E '3000|8000|389|5432|6379'`
4. Verify `.env` exists and is valid

---

### LDAP Bootstrap Fails

**Symptoms:** `ldap_bootstrap` container exits with error, or users/groups don't appear.

**Steps:**

```bash
# Re-run LDAP initialization
make bootstrap

# Re-load schemas
make schemas

# Check LDAP directly
docker compose exec ldap ldapsearch -x -b "dc=heracles,dc=local" "(objectClass=*)" dn
```

---

### Authentication Fails

**Symptoms:** Login returns 401, "Invalid credentials."

**Steps:**

1. Verify credentials in `.env` (`HRC_ADMIN_USER`, `HRC_ADMIN_PASSWORD`)
2. Check LDAP binding: `docker compose exec ldap ldapwhoami -x -D "cn=admin,dc=heracles,dc=local" -w $LDAP_ADMIN_PASSWORD`
3. Check JWT `SECRET_KEY` hasn't changed since tokens were issued
4. Look for clock skew between containers

---

### Database Migration Errors

**Symptoms:** API starts but returns 500 errors, SQLAlchemy errors in logs.

**Steps:**

```bash
make shell s=api
python -m alembic upgrade head
```

If migrations are corrupted:

```bash
python -m alembic stamp head  # Reset migration tracking
python -m alembic upgrade head
```

---

### Plugin Not Loading

**Symptoms:** Plugin tabs don't appear, 404 on plugin API endpoints.

**Steps:**

1. Check API logs for plugin loading errors: `make logs s=api | grep plugin`
2. Verify the plugin directory exists under `heracles_plugins/heracles_plugins/`
3. Check `plugin.py` has a valid `get_info()` function
4. Ensure required LDAP schemas are loaded

---

### LDAP Search Returns Empty

**Symptoms:** Users or groups exist in phpLDAPadmin but not in the Heracles UI.

**Steps:**

1. Check the search base DN matches your configuration
2. Verify the service account has read permissions
3. Check LDAP filter syntax in the API logs
4. Try a direct LDAP search: `docker compose exec ldap ldapsearch -x -b "ou=people,dc=heracles,dc=local" "(objectClass=inetOrgPerson)"`

---

### TLS Certificate Errors

**Symptoms:** Connection refused, SSL handshake failures.

**Steps:**

1. Regenerate dev certificates: `./scripts/dev-pki/generate.sh`
2. Verify the CA is trusted: `openssl verify -CAfile pki/dev/ca/heracles-dev-ca.crt pki/dev/server/heracles.local.crt`
3. Check certificate expiration: `openssl x509 -in pki/dev/server/heracles.local.crt -noout -dates`

---

## Getting Help

If you can't resolve the issue:

1. Search [existing issues](https://github.com/abdoufermat5/heracles/issues)
2. Check the API logs for the full error traceback
3. Open a new issue with:
    - Heracles version (`make version`)
    - Docker and OS versions
    - Steps to reproduce
    - Relevant log output
