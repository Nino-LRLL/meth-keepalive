"""Meth Linux — couche système native (sysfs, proc, systemd — stdlib seule).

Responsabilités (même contrat que ``src.Windows``) :
- ``Power``  : /sys/class/power_supply (secteur/batterie), polling léger ;
- ``Lid``    : /proc/acpi/button/lid (état du capot), polling léger ;
- ``System`` : systemd-inhibit (keep-alive), autostart ~/.config/autostart,
  informations système honnêtes.

Chaque classe accepte un logger ``(level, message)`` et ne lève jamais :
les erreurs sont retournées en dict / états « INCONNU » — jamais inventés.
"""
