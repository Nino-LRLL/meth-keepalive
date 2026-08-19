# ADR 0005 — Le repo GitHub s'appelle `meth-keepalive`, pas `Meth`

- **Date** : 2026-08-19 (V0.2)
- **Statut** : Accepté

## Décision

Le dépôt public GitHub se nomme **`meth-keepalive`** (propriétaire
`Nino-LRLL`). Le **produit** garde son nom **Meth** (fenêtre, exécutable,
marque, docs) ; seul le nom du **dépôt** porte le suffixe `-keepalive`.

## Contexte

La publication du projet s'est faite en grill-with-docs. La question du nom
du repo a été tranchée par l'utilisateur : `Meth` est libre sur son compte,
mais c'est aussi un terme d'argot pour la méthamphétamine — risque réel de
signalement/suppression sur un dépôt **public**, mauvais SEO, confusions.
`meth-keepalive` décrit le produit (`Meth` + ce qu'il fait) sans l'ambiguïté.

## Conséquences

- URL publique : `github.com/Nino-LRLL/meth-keepalive` (badges CI, lien
  Releases, URL de clone dans le README).
- Le nom du produit reste « Meth » partout (README titre, `Meth.exe`,
  `Meth.spec`, tray, `src/`). Aucun renommage du code — seul le nom du
  dépôt change.
- Le dossier local de publication se nomme `meth-keepalive` (cohérent avec
  l'URL de clone).

## Alternatives écartées

- **`Meth`** : marque plus courte, mais ambiguïté drogue + risque de
  signalement GitHub sur un repo public — le risque l'emporte.
- **`Meth-KeepAlive` (casse) / `meth-keepalive` (minuscules)** : GitHub
  normalise en minuscules pour l'URL ; le repo local suit la convention
  de clone (minuscules).
