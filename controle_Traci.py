import os
import sys
import traci
import asyncio
import json
import websockets
from typing import Any, cast

if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
else:
    sys.exit("Erreur: Déclarez la variable SUMO_HOME")

async def run_sumo_logic(websocket):
    print("🌐 Dashboard connecté")
    
    # Détection : Docker crée souvent un fichier /.dockerenv à la racine
    is_docker = os.path.exists('/.dockerenv')
    
    # Choix de l'exécutable
    sumo_binary = "sumo" if is_docker else "sumo-gui"
    print(f"🛠️ Lancement de {sumo_binary}...")

    sumoCmd = [sumo_binary, "-c", "simulation.sumocfg"]
    
    # Si on est dans Docker, on ajoute des options pour éviter les erreurs d'affichage
    if is_docker:
        sumoCmd.extend(["--no-warnings", "--no-step-log"])

    traci.start(sumoCmd)
    # ... reste du code ...
    
    traffic_lights = traci.trafficlight.getIDList()
    step = 0

    try:
        while True:
            # On récupère la valeur brute
            raw_expected = traci.simulation.getMinExpectedNumber()
            
            # On force la conversion en entier pour rassurer Pylance
            # Si c'est un tuple par erreur, on prend le premier élément [0]
            if isinstance(raw_expected, tuple):
                expected = int(raw_expected[0])
            else:
                expected = int(raw_expected)

            if expected <= 0:
                break
                
            traci.simulationStep()
            
            stats = {}
            for tls_id in traffic_lights:
                # 1. Identifier toutes les voies qui arrivent au carrefour
                controlled_lanes = traci.trafficlight.getControlledLanes(tls_id)
                lanes = list(set(controlled_lanes))
                
                carrefour_data = {
                    "total_attente": 0,
                    "bras": {}, # Détails par voie
                    "phase": int(traci.trafficlight.getPhase(tls_id)) # type: ignore
                }

                for l in lanes:
                    # 2. Extraire le nombre de voitures arrêtées sur ce bras spécifique
                    nb_stop = traci.lane.getLastStepHaltingNumber(l) # type: ignore
                    
                    # On convertit explicitement pour éviter les erreurs Pylance
                    count = int(nb_stop) if isinstance(nb_stop, (int, float)) else 0
                    
                    carrefour_data["bras"][l] = count
                    carrefour_data["total_attente"] += count
                
                stats[tls_id] = carrefour_data

            # 3. Envoi des données enrichies au WebSocket
            await websocket.send(json.dumps({"step": step, "data": stats}))
            
            step += 1
            await asyncio.sleep(0.01)
            
    except websockets.exceptions.ConnectionClosed:
        print("🔴 Dashboard fermé")
    finally:
        traci.close()

async def main():
    # Détection si on est dans Docker
    is_docker = os.path.exists('/.dockerenv')
    host = "0.0.0.0" if is_docker else "localhost"
    
    print(f"🚀 Serveur prêt sur ws://{host}:8765")
    async with websockets.serve(run_sumo_logic, host, 8765, ping_interval=None):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass