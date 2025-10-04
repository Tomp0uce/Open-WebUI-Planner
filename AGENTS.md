# Repository Development Guidelines

- Suivez PEP 8 et utilisez systématiquement les annotations de types Python.
- Aucune dépendance externe supplémentaire ne doit être ajoutée sans justification explicite.
- Préférez les fonctions utilitaires existantes d'Open WebUI documentées dans `docs_openwebui/`.
- Les nouveaux champs ou options doivent être documentés dans le `README.md` correspondant.
- Maintenez une journalisation cohérente via le logger défini dans `planner.py`.
- Évitez toute logique spécifique à un environnement particulier : le code doit rester générique.
