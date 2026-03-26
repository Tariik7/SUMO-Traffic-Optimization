import os
import subprocess
import sys

def generer(scenario="normal"):
    if 'SUMO_HOME' not in os.environ:
        sys.exit("Erreur : Déclarez la variable SUMO_HOME")
    
    net_file = 'reseau_12_carrefours.net.xml'
    cfg_file = 'simulation.sumocfg'
    
    # Configuration des volumes de trafic
    params = {
        "normal": {"period": "3.0", "fringe": "10"},
        "pic": {"period": "0.5", "fringe": "5"},
        "incident": {"period": "1.5", "fringe": "10"}
    }
    p = params.get(scenario, params["normal"])

    print(f"🚧 Génération du réseau (4 voies par route) et scénario: {scenario}...")

   # 1. Générer le réseau avec 2 voies par sens (Total 4)
    subprocess.run([
        'netgenerate', 
        '--grid', 
        '--grid.x-number=4', 
        '--grid.y-number=3', 
        '--grid.length=250',
        '--default.lanenumber', '2',
        '--tls.guess', 'true',         # <-- Option universelle
        '--tls.default-type', 'static', # <-- Type de feu standard
        '-o', net_file
    ], check=True)

    # 2. Générer le trafic
    sumo_home = os.environ['SUMO_HOME']
    random_trips = os.path.join(sumo_home, 'tools', 'randomTrips.py')
    subprocess.run([
        sys.executable, random_trips,
        '-n', net_file,
        '-p', p["period"],
        '--fringe-factor', p["fringe"],
        '--route-file', 'trafic.rou.xml',
        '--end', '3600'
    ], check=True)

    # 3. Créer/Vérifier le fichier de config
    config_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="{net_file}"/>
        <route-files value="trafic.rou.xml"/>
    </input>
</configuration>"""
    with open(cfg_file, "w") as f:
        f.write(config_content)

if __name__ == "__main__":
    choix = sys.argv[1] if len(sys.argv) > 1 else "normal"
    generer(choix)