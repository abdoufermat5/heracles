# Dépannage

## SSSD ne trouve pas les utilisateurs

### Vérifier la connectivité LDAP

```bash
vagrant ssh server1 -c 'ldapsearch -x -H ldap://192.168.56.1:389 -b "dc=heracles,dc=local" "(uid=testuser)" uid'
```

### Vérifier les logs SSSD

```bash
vagrant ssh server1 -c 'sudo journalctl -u sssd -n 30'
```

### Rafraîchir le cache

```bash
vagrant ssh server1 -c 'sudo sss_cache -E && sudo systemctl restart sssd'
```

### Activer le debug

```bash
vagrant ssh server1 -c 'sudo sed -i "s/debug_level = .*/debug_level = 9/" /etc/sssd/sssd.conf'
vagrant ssh server1 -c 'sudo systemctl restart sssd'
vagrant ssh server1 -c 'sudo journalctl -u sssd -f'
```

## SSH refuse la connexion

### Tester le script de récupération des clés

```bash
vagrant ssh server1 -c 'sudo /usr/local/bin/ldap-ssh-keys.sh testuser'
```

**Résultat attendu :** La clé publique SSH.

### Vérifier les permissions

```bash
vagrant ssh server1 -c 'ls -la /usr/local/bin/ldap-ssh-keys.sh'
# Doit être exécutable
```

### Vérifier les logs SSH

```bash
vagrant ssh server1 -c 'sudo journalctl -u sshd -n 20'
```

### Vérifier la clé dans LDAP

```bash
ldapsearch -x -H ldap://localhost:389 \
  -D "cn=admin,dc=heracles,dc=local" -w admin_secret \
  -b "uid=testuser,ou=people,dc=heracles,dc=local" sshPublicKey
```

## Sudo ne fonctionne pas

### Vérifier nsswitch.conf

```bash
vagrant ssh server1 -c 'grep sudoers /etc/nsswitch.conf'
# Doit afficher: sudoers: files sss
```

### Vérifier les règles dans LDAP

```bash
ldapsearch -x -H ldap://localhost:389 \
  -D "cn=admin,dc=heracles,dc=local" -w admin_secret \
  -b "ou=sudoers,dc=heracles,dc=local" "(objectClass=sudoRole)" cn sudoUser sudoCommand
```

### Rafraîchir le cache sudo

```bash
vagrant ssh server1 -c 'sudo sss_cache -s && sudo systemctl restart sssd'
```

## API ne répond pas

### Vérifier les conteneurs

```bash
docker ps | grep heracles
```

### Redémarrer l'API

```bash
cd /chemin/vers/heracles
make dev-down
make dev-up
```

### Vérifier les logs

```bash
docker logs heracles-api -f
```

## VMs ne démarrent pas

### Vérifier VirtualBox

```bash
VBoxManage list vms
VBoxManage list runningvms
```

### Recréer les VMs

```bash
cd demo
vagrant destroy -f
vagrant up
```

## Commandes utiles

```bash
# Statut Vagrant
vagrant status

# Reconfigurer une VM
vagrant provision server1

# SSH verbose
vagrant ssh server1 -- -v

# Logs SSSD en temps réel
vagrant ssh server1 -c 'sudo journalctl -u sssd -f'
```
