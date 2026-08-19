# ADR 0004 — Meth restaure son état ON après un redémarrage

- **Date** : 2026-08-18 (V0.1)
- **Statut** : Accepté

## Décision

`MethApp.start()` relit `config["last_state"]` : si l'utilisateur avait
laissé Meth **ON**, Meth se réactive automatiquement au démarrage suivant
(Windows démarre → Meth ON → l'IA peut continuer après un reboot).

## Contexte

Le scénario central de Meth : une IA travaille pendant des heures, parfois
la nuit. Un redémarrage Windows (mise à jour, coupure) ne doit pas laisser
l'utilisateur redémarrer Meth à la main. Le cahier des charges (section 26,
test 7) demande d'ailleurs de vérifier « l'état après redémarrage ».

## Conséquences

- Continuité réelle : `last_state` est persisté à chaque bascule ON/OFF.
- Le comportement reste sûr : le fail-safe natif (ADR 0001) prime — si Meth
  ne démarre pas, Windows est normal. La restauration ON n'écrase jamais la
  sécurité, elle prolonge le dernier choix explicite de l'utilisateur.
- Désactivation claire : passer OFF → `last_state = False` → au prochain
  boot Meth démarre OFF.

## Alternatives écartées

- **Toujours démarrer OFF** : plus conservateur mais casse la continuité
  d'une tâche longue après un reboot imprévu.
- **Confirmation au démarrage** : friction inutile — Meth est fait pour
  tourner sans supervision.
