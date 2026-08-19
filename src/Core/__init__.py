"""Meth Core — moteur de maintien d'activité, indépendant de l'UI et de Windows.

Sépare la LOGIQUE (activation, restauration, fail-safe, sessions) de la
COUCHE SYSTÈME (api Windows) et de l'UI (Tkinter / tray). Les dépendances
concrètes sont INJECTÉES, ce qui rend le Core testable sans Windows.
"""
