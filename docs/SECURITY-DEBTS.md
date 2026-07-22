# Dettes de sécurité actives

## 2026-07-22 — rotation Crawl4AI partagée

Lors d'une vérification du runtime Bassira, la valeur de
`CRAWL4AI_API_TOKEN` a été imprimée dans un transcript d'outil. Ce credential
est compromis au sens SOP-001.

La rotation doit être effectuée dans la session propriétaire du service
mutualisé Crawl4AI, puis propagée à chacun de ses consommateurs. Cette session
Bassira ne doit ni révoquer ni remplacer cette clé transfrontière.

La clôture exige : remplacement du credential côté service, mise à jour de tous
les consommateurs, redéploiement, puis preuve d'authentification sans afficher
la valeur du secret.
