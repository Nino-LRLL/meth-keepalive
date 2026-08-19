"""Meth Windows — couche système native (ctypes, aucune dépendance externe).

Responsabilités :
- ``Power``  : GetSystemPowerStatus (secteur/batterie), événements d'alimentation ;
- ``Lid``    : RegisterPowerSettingNotification (état du capot via GUID_LIDSWITCH) ;
- ``System`` : SetThreadExecutionState (keep-alive), démarrage avec Windows,
  informations système honnêtes.

Chaque classe accepte un logger ``(level, message)`` et ne lève jamais :
les erreurs sont retournées en dict / états « INCONNU » — jamais inventés.
"""
