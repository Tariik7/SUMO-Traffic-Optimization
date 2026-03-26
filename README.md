🚦 SUMO Traffic Control Dashboard
Ce projet est une solution de monitoring de trafic routier en temps réel utilisant SUMO (Simulation of Urban MObility) et Python. L'architecture est entièrement conteneurisée pour garantir un déploiement rapide et sans erreurs de dépendances.

🏗️ Architecture du Projet
L'application repose sur une architecture client-serveur :

Backend (Docker) : Un conteneur Ubuntu faisant tourner le moteur SUMO et un serveur WebSocket (Python) sur le port 8765.

Frontend (Navigateur) : Une page HTML5/JavaScript utilisant Chart.js pour visualiser la charge des 12 carrefours en temps réel.

🚀 Installation et Lancement
1. Prérequis
Avoir Docker Desktop installé et lancé.

Un navigateur web moderne (Chrome, Firefox, Edge).

2. Récupérer l'image
Si vous avez reçu le fichier d'archive .tar :

Bash
docker load -i sumo-project.tar
Ou si l'image est sur un registre (Docker Hub) :

Bash
docker pull <votre-pseudo>/sumo-project:latest
3. Lancer la simulation
Exécutez la commande suivante pour démarrer le moteur de simulation et exposer le port réseau :

Bash
docker run -p 8765:8765 sumo-project
4. Visualiser les données
Localisez le fichier index.html à la racine du projet.

Faites un double-clic dessus pour l'ouvrir dans votre navigateur.

Le statut doit passer à "Connecté" et les graphiques commenceront à s'animer.

🛠️ Détails pour l'Ingénieur (Stack Technique)
Conteneur : Ubuntu 22.04 LTS.

Réseau : Binding sur 0.0.0.0:8765 à l'intérieur du conteneur pour permettre l'accès externe.

Interopérabilité : Utilisation de la bibliothèque TraCI pour le pilotage du moteur de simulation via Python.

Visualisation : Flux de données JSON via WebSockets pour une latence minimale.

📁 Structure des fichiers
Dockerfile : Recette de construction de l'image.

controle_Traci.py : Serveur de logique et interface TraCI.

index.html : Dashboard de monitoring.

simulation.sumocfg : Configuration du réseau routier SUMO.