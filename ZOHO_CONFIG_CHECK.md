# Guide de Configuration Zoho - Diagnostic "Client non valide"

## Problème actuel
L'erreur "Client non valide - L'ID client transmis n'existe pas" indique que l'ID client n'est pas reconnu par Zoho.

## Points à vérifier

### 1. Domaine Zoho correct
Selon votre région, vous devez utiliser le bon domaine :

- **Europe** : `zoho.eu` 
- **Inde** : `zoho.in`
- **Australie** : `zoho.com.au`
- **International/USA** : `zoho.com`

**Configuration actuelle** : `com` (par défaut)

### 2. Correspondance avec la Console API Zoho

Vérifiez dans votre Console API Zoho :

1. **URL de redirection autorisée** doit être exactement :
   ```
   [VOTRE_URL_ODOO]/zoho/auth/callback
   ```

2. **Type d'application** : Web-based Application

3. **Domaines autorisés** : Votre domaine Odoo

### 3. Configuration Odoo requise

Dans Odoo, vous devez configurer ces paramètres système :

```
zoho.client_id        = [VOTRE_CLIENT_ID_ZOHO]
zoho.client_secret    = [VOTRE_CLIENT_SECRET_ZOHO] 
zoho.domain          = [com|eu|in|com.au selon votre région]
```

### 4. Comment diagnostiquer

1. Activez le mode debug Odoo
2. Consultez les logs après tentative d'authentification
3. Vérifiez les messages de debug ajoutés :
   - "ZOHO AUTH START DEBUG"  
   - "TOKEN EXCHANGE DEBUG"

### 5. Solutions possibles

**Si le client ID est correct mais ne fonctionne pas :**

1. **Mauvais domaine** : Changez `zoho.domain` selon votre région
2. **Restrictions IP** : Vérifiez si votre IP est autorisée dans Zoho
3. **Application désactivée** : Vérifiez le statut dans la Console API Zoho
4. **Redirect URI incorrect** : Doit correspondre exactement

### 6. Test de configuration

Pour tester votre configuration :

1. Allez sur `/zoho/auth/start` dans votre Odoo
2. Consultez les logs pour voir les paramètres envoyés
3. Comparez avec votre configuration Zoho Console

### 7. Commandes de vérification

```sql
-- Dans la base Odoo, vérifiez vos paramètres :
SELECT key, value FROM ir_config_parameter 
WHERE key LIKE 'zoho.%' OR key = 'web.base.url';
```

## Prochaines étapes

1. Vérifiez votre région Zoho et ajustez `zoho.domain`
2. Confirmez que l'URL de redirection est correcte dans Zoho Console  
3. Testez à nouveau l'authentification
4. Consultez les nouveaux logs de debug