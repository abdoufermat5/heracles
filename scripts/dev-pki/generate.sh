#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PKI_DIR="${ROOT_DIR}/pki/dev"
CA_DIR="${PKI_DIR}/ca"
SERVER_DIR="${PKI_DIR}/server"
LDAP_DIR="${PKI_DIR}/ldap"
OPENSSL_CNF="${ROOT_DIR}/scripts/dev-pki/openssl.cnf"

mkdir -p "${CA_DIR}" "${SERVER_DIR}" "${LDAP_DIR}"

CA_KEY="${CA_DIR}/heracles-dev-ca.key"
CA_CRT="${CA_DIR}/heracles-dev-ca.crt"
SERVER_KEY="${SERVER_DIR}/heracles.local.key"
SERVER_CSR="${SERVER_DIR}/heracles.local.csr"
SERVER_CRT="${SERVER_DIR}/heracles.local.crt"

LDAP_KEY="${LDAP_DIR}/ldap.heracles.local.key"
LDAP_CSR="${LDAP_DIR}/ldap.heracles.local.csr"
LDAP_CRT="${LDAP_DIR}/ldap.heracles.local.crt"

if [ ! -f "${CA_KEY}" ] || [ ! -f "${CA_CRT}" ]; then
  openssl req -new -x509 -nodes -days 3650 \
    -config "${OPENSSL_CNF}" \
    -keyout "${CA_KEY}" \
    -out "${CA_CRT}"
  chmod 600 "${CA_KEY}"
  chmod 644 "${CA_CRT}"
fi

openssl req -new -nodes \
  -config "${OPENSSL_CNF}" \
  -section server_req \
  -reqexts v3_server \
  -keyout "${SERVER_KEY}" \
  -out "${SERVER_CSR}"

openssl x509 -req -days 3650 \
  -in "${SERVER_CSR}" \
  -CA "${CA_CRT}" \
  -CAkey "${CA_KEY}" \
  -CAcreateserial \
  -extensions v3_server \
  -extfile "${OPENSSL_CNF}" \
  -out "${SERVER_CRT}"

chmod 600 "${SERVER_KEY}"
chmod 644 "${SERVER_CRT}"

openssl req -new -nodes \
  -config "${OPENSSL_CNF}" \
  -section ldap_req \
  -reqexts v3_ldap \
  -keyout "${LDAP_KEY}" \
  -out "${LDAP_CSR}"

openssl x509 -req -days 3650 \
  -in "${LDAP_CSR}" \
  -CA "${CA_CRT}" \
  -CAkey "${CA_KEY}" \
  -CAcreateserial \
  -extensions v3_ldap \
  -extfile "${OPENSSL_CNF}" \
  -out "${LDAP_CRT}"

chmod 600 "${LDAP_KEY}"
chmod 644 "${LDAP_CRT}"

echo "CA cert: ${CA_CRT}"
echo "CA key:  ${CA_KEY}"
echo "Server cert: ${SERVER_CRT}"
echo "Server key:  ${SERVER_KEY}"
echo "LDAP cert: ${LDAP_CRT}"
echo "LDAP key:  ${LDAP_KEY}"
