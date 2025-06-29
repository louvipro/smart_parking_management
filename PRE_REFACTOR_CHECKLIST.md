# Pré-Refactoring Checklist

Cette checklist doit être complétée avant de commencer le refactoring du projet en suivant le `CLEAN_ARCHITECTURE_GUIDE.md`. Elle vise à s'assurer que l'environnement de développement est prêt et que le projet est dans un état stable pour servir de point de départ.

## État du Projet et Environnement

- [ ] **Vérifier l'état de Git :**
    - [ ] S'assurer que le répertoire de travail est propre (`git status` ne doit montrer aucune modification non commitée).
    - [ ] S'assurer que la branche actuelle est la bonne pour le refactoring (ex: `refactor/clean-architecture`).
    - [ ] Pousser toutes les modifications locales sur le dépôt distant pour sauvegarder le travail actuel.

- [ ] **Installer les dépendances :**
    - [ ] Exécuter `make install-dev` pour s'assurer que toutes les dépendances du projet sont installées et que l'environnement `uv` est correctement configuré.

- [ ] **Initialiser la base de données :**
    - [ ] Exécuter `python src/init_database.py` pour s'assurer que la base de données est créée et peuplée avec des données initiales.

## Vérification Fonctionnelle de Base

- [ ] **Lancer l'application frontend :**
    - [ ] Exécuter `make run-frontend` et vérifier que l'application Streamlit démarre sans erreur et que l'interface utilisateur est accessible dans le navigateur.
    - [ ] Effectuer quelques interactions de base (ex: ajouter un véhicule, simuler une entrée/sortie si possible via l'UI).

- [ ] **Exécuter les tests existants :**
    - [ ] Exécuter `make test` pour s'assurer que tous les tests unitaires existants passent. Ces tests serviront de "filet de sécurité" et de référence pour le refactoring. Si des tests échouent à ce stade, ils doivent être corrigés avant de commencer le refactoring.

## Préparation au Refactoring

- [ ] **Comprendre l'état actuel :**
    - [ ] Relire le `AGENTS.md` et le `CLEAN_ARCHITECTURE_GUIDE.md` pour bien comprendre les objectifs et les principes du refactoring.
    - [ ] Identifier les zones du code qui nécessitent le plus d'attention (ex: les violations de dépendances, les problèmes de `datetime` identifiés).
