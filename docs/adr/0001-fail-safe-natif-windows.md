# ADR 0001 — Fail-safe natif par Windows, pas de démon de restauration

- **Date** : 2026-08-18 (V0.1)
- **Statut** : Accepté

## Décision

Meth ne déploie **aucun** mécanisme de restauration compliqué (démon de
surveillance, ré-armement périodique, cleanup au boot). Le fail-safe repose
sur le comportement natif de `SetThreadExecutionState` : **Windows efface
l'état d'exécution demandé quand le processus qui l'a demandé meurt**
(crash, fin de session, redémarrage). Meth ajoute seulement un `shutdown()`
explicite (`ES_OFF`) au quit propre.

## Contexte

Le cahier des charges demandait un fail-safe pour « ne jamais laisser
Windows dans un état dangereux » (crash, reboot, session expirée). Les
alternatives : un agent de nettoyage lancé au boot, une restauration
périodique, ou un verrou d'état fichier/registre.

## Conséquences

- Zéro état dangereux persistant possible : même un `kill -9` de Meth rend
  Windows à son comportement normal.
- `restore_previous()` existe et est testé (rejouer l'état mémorisé) mais
  n'est **pas branché** au flux principal — c'est une brique documentée pour
  un futur usage, pas une dépendance.
- Le code reste petit et testable : pas de daemon à synchroniser.

## Alternatives écartées

- **Démon de restauration au boot** : complexité inutile, Windows fait déjà
  le travail.
- **Registre d'état persistant** : fragile (écriture/lecture, corruption),
  aucun bénéfice sur le natif.
