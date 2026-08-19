# CONTEXT — Glossaire du domaine Meth

Termes spécifiques au projet. 1-2 phrases chacun : ce que c'est, pas ce que ça
fait.

## Méth (Keep-Alive)

- **Meth** — l'application : une petite fenêtre qui maintient le système
  éveillé quand on ferme le capot, pendant que l'IA / un script / une
  compilation travaille encore. **Windows ET Linux** (macOS : non supporté,
  repli honnête — jamais de keep-alive prétendu).
- **Keep-Alive** — le moteur de Meth : demande au système de rester actif
  sans garder l'écran allumé. C'est l'état ON. Windows :
  `SetThreadExecutionState(ES_SYSTEM_REQUIRED)` ; Linux :
  `systemd-inhibit --what=sleep:handle-lid-switch`.
- **ON / OFF** — les deux états de Meth. ON = le PC reste actif capot
  fermé ; OFF = comportement système normal. Pas d'état intermédiaire en V0.
- **Fail-safe** — la garantie que le système revient à un état sûr si Meth
  meurt (crash, reboot, fin de session). Nativement assuré : Windows efface
  l'état d'exécution à la mort du processus, systemd relâche l'inhibiteur à
  la mort du process qui le porte. Renforcé par un `shutdown()` explicite au
  quit.

## Matériel et énergie

- **Capot (lid)** — l'état de l'écran pliable d'un portable. `OUVERT`,
  `FERMÉ` ou `INCONNU` (jamais inventé : Windows n'expose pas toujours cette
  information). C'est le déclencheur du problème que Meth résout.
- **Alimentation** — `SECTEUR` (branché), `BATTERIE` (sur batterie, avec
  pourcentage) ou `INCONNUE`. La V0 n'agit pas sur l'alimentation ; la V0.2
  prévoit un comportement batterie (auto-off sur batterie faible).
- **PC** — l'état affiché de la machine : `ACTIF` quand Meth maintient
  Windows éveillé, `NORMAL` sinon. N'est jamais « VEILLE » : Meth ne sait
  pas si le PC est réellement en veille, il ne ment pas.

## Publication (v0.2)

- **meth-keepalive** — le nom du **repo** GitHub public (`Nino-LRLL`),
  distinct du nom du produit. Le produit s'appelle **Meth** (fenêtre, exe,
  marque) ; le repo porte `-keepalive` car « Meth » seul est ambigu (argot
  drogue → risque de signalement/suppression sur GitHub). Voir ADR `0005`.
- **_Avoid_** : « repo Meth » — on dit `meth-keepalive` pour le dépôt,
  « Meth » pour l'application.

## Plateformes (v0.2)

- **Backend** — l'implémentation native sélectionnée par `src/backends.py`
  selon la plateforme : `windows` (ctypes) ou `linux` (systemd/sysfs/proc),
  sinon repli honnête (keep-alive indisponible, jamais simulé).
- **systemd-inhibit** — l'équivalent Linux de `ES_SYSTEM_REQUIRED` : un
  processus `systemd-inhibit --what=sleep:handle-lid-switch --mode=block`
  bloque la veille ET l'action fermeture du capot. Écran libre de s'éteindre.
  Processus tué à l'arrêt de Meth → systemd relâche l'inhibiteur (fail-safe).
- **sysfs** — `/sys/class/power_supply` : lecture de l'alimentation sur
  Linux (type Mains → online ; type Battery → capacity).
- **ACPI lid** — `/proc/acpi/button/lid/*/state` : état du capot sur Linux
  (polling léger, `INCONNU` si absent).

## Paramètres (Config)

- **Autostart** — démarre Meth avec la session : clé registre
  `HKCU\...\Run` sur Windows, `~/.config/autostart/meth.desktop` sur Linux.
  Sans admin. Option décochée par défaut.
- **System Tray** — Meth continue de tourner en arrière-plan après fermeture
  de la fenêtre. Fermer la fenêtre ≠ quitter Meth.
- **Secteur uniquement (ac_only)** — refus d'activer Meth sur batterie.
  Option décocée par défaut.
- **Dernier état (last_state)** — Meth restaure son état ON au redémarrage
  si l'utilisateur l'avait laissé ON (continuité : une IA qui travaillait
  continue après un reboot). Voir ADR `0004`.
- **Config** — fichier JSON dans `%APPDATA%\Meth\config.json` (Windows) ou
  `~/.config/meth/config.json` (Linux) — jamais dans le dossier de l'exe :
  Meth reste portable et multi-utilisateurs. Voir ADR `0003`.

## À venir (V0.2+)

- **Session** — une unité de travail déclarée par une IA (« je compile
  encore ») : owner, raison, priorité, durée, heartbeat. Prête dans le code
  (`src/Core/KeepAlive.py`) mais non branchée en V0.
- **Heartbeat** — le signal « je travaille encore » qu'une IA pourra
  envoyer à Meth pour prolonger son keep-alive.
- **Profil** — (V0.2) un ensemble de réglages nommé (timeout, comportement
  batterie) pour un cas d'usage (build, téléchargement, veille sur batterie).

_Avoid_ : « veille » pour l'état du PC (Meth ne le connaît pas) ;
« capot inconnu » pour « capot non détecté » (on dit `INCONNU`, état
honnête).
