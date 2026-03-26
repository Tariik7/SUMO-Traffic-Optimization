import os
import subprocess # <--- C'est cette ligne qui manquait !
import sys

# 1. Vérification de la variable SUMO_HOME
if 'SUMO_HOME' not in os.environ:
    sys.exit("Erreur : Déclarez la variable d'environnement 'SUMO_HOME' avant de lancer le script.")

# 2. Génération du réseau (Les 12 carrefours avec feux)
print("🚧 Génération du réseau routier (12 carrefours avec feux)...")

# Nous essayons plusieurs options pour être sûr que les feux sont activés 
# selon votre version de SUMO.
try:
    subprocess.run([
        'netgenerate', 
        '--grid', 
        '--grid.x-number=4', 
        '--grid.y-number=3', 
        '--grid.length=200', 
        '--grid.traffic-light', 'true',
        '-o', 'reseau_12_carrefours.net.xml'
    ], check=True)
    
    print("✅ Réseau généré avec succès.")
except subprocess.CalledProcessError:
    print("⚠️ Erreur avec les options standards, tentative avec l'option alternative...")
    subprocess.run([
        'netgenerate', 
        '--grid', 
        '--grid.x-number=4', 
        '--grid.y-number=3', 
        '--grid.length=200', 
        '--default-junction-type', 'traffic_light',
        '-o', 'reseau_12_carrefours.net.xml'
    ], check=True)

# 3. Génération du trafic aléatoire
print("🚗 Génération des véhicules...")
sumo_home = os.environ['SUMO_HOME']
random_trips_path = os.path.join(sumo_home, 'tools', 'randomTrips.py')

subprocess.run([
    sys.executable, random_trips_path, 
    '-n', 'reseau_12_carrefours.net.xml', 
    '-e', '3600', 
    '-p', '2.5',  # <-- On passe à 2.5 pour réduire le nombre de voitures
    '--fringe-factor', '10', # Favorise les trajets qui traversent tout le réseau
    '--route-file', 'trafic.rou.xml'
], check=True)

# 4. Création du fichier de configuration SUMO
config_content = """<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="reseau_12_carrefours.net.xml"/>
        <route-files value="trafic.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
</configuration>"""

with open("simulation.sumocfg", "w") as f:
    f.write(config_content)

print("🚀 Fichiers prêts ! Vous pouvez maintenant lancer 'controle_traci.py'")