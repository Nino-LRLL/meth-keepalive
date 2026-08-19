# ADR 0003 — Config dans %APPDATA%, pas à côté de l'exe

- **Date** : 2026-08-18 (V0.1)
- **Statut** : Accepté

## Décision

La configuration de Meth est un JSON dans `%APPDATA%\Meth\config.json`
(`Config.default_path()`), **pas** un fichier dans le dossier de l'exe.

## Contexte

Meth est distribué en portable (`Meth-Portable.zip`) mais aussi installable.
Si la config vivait à côté de l'exe : dossier d'installation en lecture seule
(PROGRAMFILES), config perdue à chaque mise à jour, conflits multi-utilisateurs
sur un même poste. `%APPDATA%` est le standard Windows pour les réglages
utilisateur.

## Conséquences

- Le portable reste réellement portable : on peut le déplacer/copier sans
  perdre les réglages (ils vivent ailleurs).
- Multi-utilisateurs propre : chacun a sa config.
- Mises à jour sans écrasement : l'exe est remplacé, la config survit.
- Contrepartie assumée : le portable n'emporte pas ses réglages sur une
  autre machine (choix de conception — le programme est portable, pas les
  préférences).

## Alternatives écartées

- **Config à côté de l'exe** : cassée par ProgramFiles/lecture seule et par
  les mises à jour.
- **Registre Windows** : moins lisible, plus fragile à sauvegarder,
  pas de fallback multi-plateforme.
