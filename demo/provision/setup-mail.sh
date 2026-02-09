#!/bin/bash
# =============================================================================
# Heracles Demo - Mail Server Setup (Postfix + Dovecot)
# =============================================================================
# This script configures a complete mail server with:
#   - Postfix (SMTP/Submission/SMTPS) with LDAP virtual mailbox maps
#   - Dovecot (IMAP/IMAPS + LMTP) with direct LDAP authentication
#   - Self-signed TLS certificates (STARTTLS + implicit TLS)
#   - Sieve for vacation auto-reply (synced from LDAP)
#   - Quota enforcement via Dovecot
#   - Roundcube Webmail (Nginx + PHP-FPM) at https://mail.<domain>
#
# Authentication: Direct LDAP simple bind (no SSSD dependency)
# Mailboxes: Virtual (Maildir under /var/mail/vhosts/)
#
# Configuration is loaded from /vagrant/config/demo.conf
# Templates are in /vagrant/config/templates/
# =============================================================================

set -e

# Load configuration
CONFIG_DIR="/vagrant/config"
source "${CONFIG_DIR}/demo.conf"

echo "=============================================="
echo "  Heracles Demo - Mail Server Setup"
echo "=============================================="
echo "LDAP Server: ${LDAP_HOST}:${LDAP_PORT}"
echo "Base DN: ${LDAP_BASE_DN}"
echo "Mail Domain: ${MAIL_DOMAIN}"
echo "Mail Server: ${MAIL_SERVER}"
echo "Auth: Direct LDAP bind"
echo "TLS: Self-signed (STARTTLS + implicit)"
echo "=============================================="

# =============================================================================
# [1/11] Install packages
# =============================================================================
echo "[1/11] Installing Postfix, Dovecot, Roundcube, and dependencies..."
export DEBIAN_FRONTEND=noninteractive

# Pre-seed Postfix configuration to avoid interactive prompts
debconf-set-selections <<< "postfix postfix/mailname string ${MAIL_SERVER}"
debconf-set-selections <<< "postfix postfix/main_mailer_type string 'Internet Site'"

apt-get update -qq
apt-get install -y -qq \
    postfix \
    postfix-ldap \
    dovecot-core \
    dovecot-imapd \
    dovecot-lmtpd \
    dovecot-ldap \
    dovecot-sieve \
    dovecot-managesieved \
    ldap-utils \
    ca-certificates \
    openssl \
    mailutils \
    swaks \
    nginx \
    php-fpm \
    php-mbstring \
    php-xml \
    php-intl \
    php-zip \
    php-pdo \
    php-sqlite3 \
    php-curl \
    php-gd \
    php-imagick \
    php-ldap \
    roundcube \
    roundcube-sqlite3 \
    roundcube-plugins \
    2>/dev/null

# =============================================================================
# [2/11] Create vmail user for virtual mailbox storage
# =============================================================================
echo "[2/11] Creating vmail user and mailbox directory..."

groupadd -g "${VMAIL_GID}" vmail 2>/dev/null || true
useradd -u "${VMAIL_UID}" -g vmail -s /usr/sbin/nologin \
    -d "${VMAIL_HOME}" -m vmail 2>/dev/null || true

mkdir -p "${VMAIL_HOME}/${MAIL_DOMAIN}"
chown -R vmail:vmail "${VMAIL_HOME}"
chmod -R 770 "${VMAIL_HOME}"

echo "✅ vmail user (uid=${VMAIL_UID}) and ${VMAIL_HOME} created"

# =============================================================================
# [3/11] Install dev CA and TLS certificate
# =============================================================================
echo "[3/11] Installing TLS certificate..."

mkdir -p "$(dirname "${MAIL_TLS_CERT}")" "$(dirname "${MAIL_TLS_KEY}")"

if [ -f "${DEV_CA_CERT_SOURCE}" ]; then
    cp "${DEV_CA_CERT_SOURCE}" "${LDAP_CA_CERT}"
    update-ca-certificates 2>/dev/null || true
else
    echo "⚠️  Dev CA not found at ${DEV_CA_CERT_SOURCE}"
fi

if [ -f "${DEV_TLS_CERT_SOURCE}" ] && [ -f "${DEV_TLS_KEY_SOURCE}" ]; then
    cp "${DEV_TLS_CERT_SOURCE}" "${MAIL_TLS_CERT}"
    cp "${DEV_TLS_KEY_SOURCE}" "${MAIL_TLS_KEY}"
else
    echo "❌ Dev TLS cert/key not found in ${DEV_TLS_CERT_SOURCE} / ${DEV_TLS_KEY_SOURCE}"
    exit 1
fi

chmod 600 "${MAIL_TLS_KEY}"
chmod 644 "${MAIL_TLS_CERT}"

echo "✅ TLS certificate: ${MAIL_TLS_CERT}"
echo "   TLS key: ${MAIL_TLS_KEY}"

# =============================================================================
# [4/11] Configure Postfix
# =============================================================================
echo "[4/11] Configuring Postfix..."

# Main configuration
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/postfix-main.cf.template" \
    /etc/postfix/main.cf

# Master process configuration (submission + smtps)
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/postfix-master.cf.template" \
    /etc/postfix/master.cf

# LDAP lookup: virtual mailbox maps (mail → mailbox path)
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/postfix-ldap-virtual-mailbox.cf.template" \
    /etc/postfix/ldap-virtual-mailbox.cf

# LDAP lookup: virtual alias maps (alternate address → primary)
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/postfix-ldap-virtual-alias.cf.template" \
    /etc/postfix/ldap-virtual-alias.cf

# LDAP lookup: forwarding maps (mail → forwarding addresses)
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/postfix-ldap-virtual-forward.cf.template" \
    /etc/postfix/ldap-virtual-forward.cf

# LDAP lookup: group mail (group mail → member expansion)
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/postfix-ldap-group-mail.cf.template" \
    /etc/postfix/ldap-group-mail.cf

# Secure LDAP config files (contain bind credentials)
chmod 640 /etc/postfix/ldap-*.cf
chown root:postfix /etc/postfix/ldap-*.cf

# Set up aliases
echo "postmaster: root" > /etc/aliases
echo "root: postmaster@${MAIL_DOMAIN}" >> /etc/aliases
newaliases 2>/dev/null || true

echo "✅ Postfix configured (SMTP:${SMTP_PORT}, Submission:${SUBMISSION_PORT}, SMTPS:${SMTPS_PORT})"

# =============================================================================
# [5/11] Configure Dovecot
# =============================================================================
echo "[5/11] Configuring Dovecot..."

# Back up default configuration
cp -a /etc/dovecot/dovecot.conf /etc/dovecot/dovecot.conf.orig 2>/dev/null || true

# Main Dovecot configuration
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/dovecot.conf.template" \
    /etc/dovecot/dovecot.conf

# LDAP authentication configuration (direct LDAP bind)
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/dovecot-ldap.conf.ext.template" \
    /etc/dovecot/dovecot-ldap.conf.ext

chmod 600 /etc/dovecot/dovecot-ldap.conf.ext

# Disable default auth includes that conflict with our config
# Our dovecot.conf does NOT include auth-system.conf.ext
for f in /etc/dovecot/conf.d/10-auth.conf \
         /etc/dovecot/conf.d/10-mail.conf \
         /etc/dovecot/conf.d/10-master.conf \
         /etc/dovecot/conf.d/10-ssl.conf \
         /etc/dovecot/conf.d/15-lda.conf \
         /etc/dovecot/conf.d/15-mailboxes.conf \
         /etc/dovecot/conf.d/20-imap.conf \
         /etc/dovecot/conf.d/20-lmtp.conf \
         /etc/dovecot/conf.d/90-quota.conf \
         /etc/dovecot/conf.d/90-sieve.conf; do
    [ -f "$f" ] && mv "$f" "${f}.disabled" 2>/dev/null || true
done

echo "✅ Dovecot configured (IMAP:${IMAP_PORT}, IMAPS:${IMAPS_PORT}, auth=LDAP bind)"

# =============================================================================
# [6/11] Set up Sieve for vacation auto-reply
# =============================================================================
echo "[6/11] Setting up Sieve directories and default scripts..."

mkdir -p /etc/dovecot/sieve/{global,before.d,after.d}

# Default sieve script (no-op, just ensures sieve infrastructure works)
cat > /etc/dovecot/sieve/default.sieve << 'SIEVE'
require ["fileinto", "mailbox"];

# Default: deliver to INBOX (no-op, just ensures Sieve pipeline runs)
keep;
SIEVE

# Compile default sieve
sievec /etc/dovecot/sieve/default.sieve 2>/dev/null || true

# Placeholder sieve scripts for spam reporting (IMAPSieve)
cat > /etc/dovecot/sieve/report-spam.sieve << 'SIEVE'
require ["vnd.dovecot.pipe", "copy", "imapsieve"];
# Placeholder: would pipe to spam learning tool (e.g., rspamd)
SIEVE

cat > /etc/dovecot/sieve/report-ham.sieve << 'SIEVE'
require ["vnd.dovecot.pipe", "copy", "imapsieve"];
# Placeholder: would pipe to ham learning tool (e.g., rspamd)
SIEVE

sievec /etc/dovecot/sieve/report-spam.sieve 2>/dev/null || true
sievec /etc/dovecot/sieve/report-ham.sieve 2>/dev/null || true

chown -R vmail:vmail /etc/dovecot/sieve/

# Quota warning script
cat > /usr/local/bin/quota-warning.sh << 'SCRIPT'
#!/bin/bash
PERCENT=$1
USER=$2
cat << EOF | /usr/lib/dovecot/dovecot-lda -d $USER -o "plugin/quota=maildir:User quota:noenforcing"
From: postmaster@$(hostname -d)
Subject: Mailbox quota warning

Your mailbox is now ${PERCENT}% full. Please delete some messages or contact your administrator.
EOF
SCRIPT
chmod +x /usr/local/bin/quota-warning.sh

echo "✅ Sieve configured (vacation, quota warnings)"

# =============================================================================
# [7/11] Install LDAP vacation sync script
# =============================================================================
echo "[7/11] Installing LDAP vacation sync..."

bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/ldap-vacation-sync.sh.template" \
    /usr/local/bin/ldap-vacation-sync.sh

chmod 755 /usr/local/bin/ldap-vacation-sync.sh

# Cron job for periodic vacation sync
cat > /etc/cron.d/ldap-vacation-sync << EOF
# Sync vacation auto-reply settings from LDAP every 5 minutes
*/5 * * * * root /usr/local/bin/ldap-vacation-sync.sh >/dev/null 2>&1
EOF

# Systemd timer as alternative
cat > /etc/systemd/system/ldap-vacation-sync.service << EOF
[Unit]
Description=Sync vacation auto-reply from LDAP
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/ldap-vacation-sync.sh
EOF

cat > /etc/systemd/system/ldap-vacation-sync.timer << EOF
[Unit]
Description=Run LDAP vacation sync every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable ldap-vacation-sync.timer
systemctl start ldap-vacation-sync.timer

echo "✅ Vacation sync installed (every 5 minutes from LDAP)"

# =============================================================================
# [8/11] Start services
# =============================================================================
echo "[8/11] Starting mail services..."

# Validate Postfix configuration
echo "  Validating Postfix configuration..."
if postfix check 2>/dev/null; then
    echo "  ✅ Postfix configuration valid"
else
    echo "  ⚠️  Postfix check warnings (may be non-fatal):"
    postfix check 2>&1 | head -5
fi

# Enable and start Postfix
systemctl enable postfix
systemctl restart postfix

sleep 2
if systemctl is-active --quiet postfix; then
    echo "  ✅ Postfix is running"
else
    echo "  ❌ Postfix failed to start"
    journalctl -u postfix --no-pager -n 10
fi

# Enable and start Dovecot
systemctl enable dovecot
systemctl restart dovecot

sleep 2
if systemctl is-active --quiet dovecot; then
    echo "  ✅ Dovecot is running"
else
    echo "  ❌ Dovecot failed to start"
    journalctl -u dovecot --no-pager -n 10
fi

# =============================================================================
# [9/11] Configure Roundcube Webmail
# =============================================================================
echo "[9/11] Configuring Roundcube Webmail..."

# Roundcube config from template
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/roundcube-config.php.template" \
    /etc/roundcube/config.inc.php

# Ensure Roundcube directories exist with correct permissions
mkdir -p /var/lib/roundcube/{db,logs,temp}
chown -R www-data:www-data /var/lib/roundcube/{db,logs,temp}
chmod -R 750 /var/lib/roundcube/{db,logs,temp}
chown www-data:www-data /etc/roundcube/config.inc.php
chmod 640 /etc/roundcube/config.inc.php

# Initialize Roundcube SQLite database
if [ ! -f /var/lib/roundcube/db/roundcube.db ]; then
    # Roundcube ships with SQL schema files
    SCHEMA_FILE=""
    for candidate in /usr/share/roundcube/SQL/sqlite.initial.sql \
                     /usr/share/dbconfig-common/data/roundcube/install/sqlite3 \
                     /var/lib/roundcube/SQL/sqlite.initial.sql; do
        if [ -f "$candidate" ]; then
            SCHEMA_FILE="$candidate"
            break
        fi
    done
    if [ -n "$SCHEMA_FILE" ]; then
        sqlite3 /var/lib/roundcube/db/roundcube.db < "$SCHEMA_FILE"
        echo "  ✅ Roundcube database initialized"
    else
        echo "  ⚠️  Roundcube SQL schema not found, database will auto-init on first access"
    fi
    chown www-data:www-data /var/lib/roundcube/db/roundcube.db 2>/dev/null || true
fi

# Increase PHP upload limits for attachments
PHP_INI=$(find /etc/php/ -name "php.ini" -path "*/fpm/*" 2>/dev/null | head -1)
if [ -n "$PHP_INI" ]; then
    sed -i 's/upload_max_filesize = .*/upload_max_filesize = 25M/' "$PHP_INI"
    sed -i 's/post_max_size = .*/post_max_size = 30M/' "$PHP_INI"
    sed -i 's/memory_limit = .*/memory_limit = 256M/' "$PHP_INI"
fi

echo "✅ Roundcube configured (skin: elastic, DB: SQLite)"

# =============================================================================
# [10/11] Configure Nginx as Webmail Frontend
# =============================================================================
echo "[10/11] Configuring Nginx for Roundcube..."

# Nginx config from template
bash "${CONFIG_DIR}/process_template.sh" \
    "${CONFIG_DIR}/templates/nginx-roundcube.conf.template" \
    /etc/nginx/sites-available/roundcube

# Enable the site, disable default
ln -sf /etc/nginx/sites-available/roundcube /etc/nginx/sites-enabled/roundcube
rm -f /etc/nginx/sites-enabled/default

# Test and start Nginx
if nginx -t 2>/dev/null; then
    echo "  ✅ Nginx configuration valid"
else
    echo "  ⚠️  Nginx config warnings:"
    nginx -t 2>&1 | head -5
fi

# Restart PHP-FPM
PHP_FPM_SERVICE=$(systemctl list-unit-files | grep 'php.*fpm' | awk '{print $1}' | head -1)
if [ -n "$PHP_FPM_SERVICE" ]; then
    systemctl enable "$PHP_FPM_SERVICE"
    systemctl restart "$PHP_FPM_SERVICE"
    sleep 1
    if systemctl is-active --quiet "$PHP_FPM_SERVICE"; then
        echo "  ✅ PHP-FPM is running ($PHP_FPM_SERVICE)"
    else
        echo "  ❌ PHP-FPM failed to start"
    fi
fi

# Start Nginx
systemctl enable nginx
systemctl restart nginx

sleep 1
if systemctl is-active --quiet nginx; then
    echo "  ✅ Nginx is running"
else
    echo "  ❌ Nginx failed to start"
    journalctl -u nginx --no-pager -n 10
fi

echo "✅ Webmail available at https://mail.${MAIL_DOMAIN}"

# =============================================================================
# [11/11] Verification
# =============================================================================
echo ""
echo "[11/11] Running verification checks..."
echo ""

# Test LDAP connectivity
echo "Testing LDAP connectivity..."
if LDAPTLS_CACERT="${LDAP_CA_CERT}" LDAPTLS_REQCERT=hard ldapsearch -x -H "ldaps://${LDAP_HOST}:${LDAP_PORT}" \
    -b "${LDAP_BASE_DN}" \
    -D "${LDAP_BIND_DN}" -w "${LDAP_BIND_PASSWORD}" \
    "(objectClass=organization)" dn 2>/dev/null | grep -q "dn:"; then
    echo "  ✅ LDAP connection successful"
else
    echo "  ⚠️  LDAP connection test failed (server may not be ready)"
fi

# Test Postfix is listening
echo "Testing Postfix ports..."
for port in ${SMTP_PORT} ${SUBMISSION_PORT} ${SMTPS_PORT}; do
    if ss -tlnp | grep -q ":${port} "; then
        echo "  ✅ Port ${port} is listening"
    else
        echo "  ⚠️  Port ${port} is NOT listening"
    fi
done

# Test Dovecot is listening
echo "Testing Dovecot ports..."
for port in ${IMAP_PORT} ${IMAPS_PORT}; do
    if ss -tlnp | grep -q ":${port} "; then
        echo "  ✅ Port ${port} is listening"
    else
        echo "  ⚠️  Port ${port} is NOT listening"
    fi
done

# Test Nginx/Webmail is listening
echo "Testing Webmail ports..."
for port in 80 443; do
    if ss -tlnp | grep -q ":${port} "; then
        echo "  ✅ Port ${port} is listening"
    else
        echo "  ⚠️  Port ${port} is NOT listening"
    fi
done

# Test TLS certificate
echo "Testing TLS certificate..."
if openssl x509 -in "${MAIL_TLS_CERT}" -noout -subject 2>/dev/null | grep -q "${MAIL_SERVER}"; then
    EXPIRY=$(openssl x509 -in "${MAIL_TLS_CERT}" -noout -enddate 2>/dev/null | cut -d= -f2)
    echo "  ✅ TLS certificate valid (CN=${MAIL_SERVER}, expires: ${EXPIRY})"
else
    echo "  ⚠️  TLS certificate check failed"
fi

echo ""
echo "=============================================="
echo "  Mail Server Setup Complete!"
echo "=============================================="
echo ""
echo "  Hostname:     ${MAIL_SERVER}"
echo "  IP:           ${MAIL1_IP}"
echo "  Domain:       ${MAIL_DOMAIN}"
echo "  Auth:         Direct LDAP bind (uid + password)"
echo ""
echo "  Ports:"
echo "    SMTP:       ${SMTP_PORT}  (STARTTLS)"
echo "    Submission: ${SUBMISSION_PORT} (STARTTLS required, SASL auth)"
echo "    SMTPS:      ${SMTPS_PORT} (implicit TLS, SASL auth)"
echo "    IMAP:       ${IMAP_PORT} (STARTTLS)"
echo "    IMAPS:      ${IMAPS_PORT} (implicit TLS)"
echo "    HTTP:       80  (redirect → HTTPS)"
echo "    HTTPS:      443 (Roundcube Webmail)"
echo ""
echo "  TLS:          Self-signed (${MAIL_TLS_CERT})"
echo "  Mailboxes:    ${VMAIL_HOME}/${MAIL_DOMAIN}/<user>/Maildir/"
echo "  Webmail:      https://mail.${MAIL_DOMAIN}  (Roundcube)"
echo ""
echo "  ⚠️  Users need hrcMailAccount activated via the Heracles API"
echo "     before they can authenticate to the mail server."
echo ""
echo "  Test commands:"
echo "    # Send test mail (from local network, no auth needed):"
echo "    swaks --to testuser@${MAIL_DOMAIN} --from admin@${MAIL_DOMAIN} \\"
echo "          --server ${MAIL1_IP}:${SMTP_PORT} --body 'Hello from Heracles!'"
echo ""
echo "    # Send via submission (authenticated, STARTTLS):"
echo "    swaks --to devuser@${MAIL_DOMAIN} --from testuser@${MAIL_DOMAIN} \\"
echo "          --server ${MAIL1_IP}:${SUBMISSION_PORT} --tls \\"
echo "          --auth-user testuser --auth-password Testpassword123"
echo ""
echo "    # Webmail (add to /etc/hosts: ${MAIL1_IP} mail.${MAIL_DOMAIN}):"
echo "    open https://mail.${MAIL_DOMAIN}"
echo "    # Login: testuser / Testpassword123"
echo ""
echo "    # Check IMAP (with TLS):"
echo "    openssl s_client -connect ${MAIL1_IP}:${IMAPS_PORT} -quiet"
echo ""
echo "    # List user mailbox:"
echo "    doveadm mailbox list -u testuser"
echo ""
