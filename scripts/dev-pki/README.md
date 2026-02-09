# Dev PKI (heracles.local)

This generates a local root CA and a wildcard server cert for `heracles.local`.

## Usage

```bash
chmod +x ./scripts/dev-pki/generate.sh
./scripts/dev-pki/generate.sh
```

## Outputs

- CA cert: `pki/dev/ca/heracles-dev-ca.crt`
- CA key: `pki/dev/ca/heracles-dev-ca.key`
- Server cert: `pki/dev/server/heracles.local.crt`
- Server key: `pki/dev/server/heracles.local.key`
- LDAP cert: `pki/dev/ldap/ldap.heracles.local.crt`
- LDAP key: `pki/dev/ldap/ldap.heracles.local.key`

## Trust the CA (host)

Linux (Debian/Ubuntu):

```bash
sudo cp pki/dev/ca/heracles-dev-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```
