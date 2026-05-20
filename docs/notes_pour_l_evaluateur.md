# Notes Pour L'Evaluateur

Bonjour,

Vous pouvez tester Procuratio via les liens et comptes ci-dessous.

## Acces public
1. API Health: `https://procuratio-production.up.railway.app/health`
2. API Docs (Swagger): `https://procuratio-production.up.railway.app/docs`
3. Customer Web: `https://customer-web-production-f032.up.railway.app`
4. Backoffice Web: `https://backoffice-web-production-2b70.up.railway.app`

## Comptes de test
1. `admin@procuratio.demo` / `Admin123!`
2. `manager@procuratio.demo` / `Manager123!`
3. `staff@procuratio.demo` / `Staff123!`
4. `customer@procuratio.demo` / `Customer123!`

## Important (frontends)
Au premier chargement des interfaces web, verifier le champ `API Base URL` et renseigner:
`https://procuratio-production.up.railway.app`

A faire sur:
1. Customer Web
2. Backoffice Web

## Parcours de validation conseille
1. Verifier que `/health` retourne `status: ok`.
2. Se connecter sur Backoffice avec `staff` et tester POS (creation ticket, ajout lignes, checkout).
3. Se connecter sur Customer Web avec `customer` et tester catalogue/panier/commande.
4. Tester prise de rendez-vous (disponibilites + reservation).
5. Tester bons cadeaux (creation/achat + suivi).
6. Verifier statistiques et campagnes.

## Notes
1. Les controles d'acces par role sont actifs (`403` attendu hors permissions).
2. Aucune configuration locale supplementaire n'est requise pour tester l'environnement public.
