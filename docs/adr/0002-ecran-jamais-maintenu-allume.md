# ADR 0002 — L'écran n'est jamais maintenu allumé

- **Date** : 2026-08-18 (V0.1)
- **Statut** : Accepté

## Décision

Meth demande `ES_CONTINUOUS | ES_SYSTEM_REQUIRED` — et **jamais**
`ES_DISPLAY_REQUIRED`. L'écran peut (et doit) s'éteindre normalement quand
le capot se ferme : Meth maintient Windows actif, pas l'écran.

## Contexte

Le cahier des charges (sections 20 et 23) est explicite : « CAPOT FERMÉ →
ÉCRAN OFF → WINDOWS ACTIF ». L'utilisateur ferme le capot ; l'écran s'éteint
(vie privée, consommation) ; les tâches IA continuent. Beaucoup d'utilitaires
« keep-awake » gardent l'écran allumé par réflexe — c'est l'inverse voulu ici.

## Conséquences

- Écran éteint dès le capot fermé (aucun réglage écran à toucher).
- Consommation minimale : pas de rétroéclairage, pas de GPU inutile.
- L'API reste honnête : Meth « garde le système actif », jamais « garde
  l'écran allumé ».

## Alternatives écartées

- **`ES_DISPLAY_REQUIRED`** : garderait l'écran allumé capot fermé — à
  l'opposé de l'objectif (et consommerait de l'énergie pour rien).
- **Simulation d'activité (souris/clavier)** : interdit par le cahier des
  charges (section 22) — hack qui trompe Windows au lieu d'utiliser l'API
  native.
