import os
import sys
import traci
import asyncio
import json
import websockets
import subprocess

# Configuration de l'environnement SUMO
if 'SUMO_HOME' in os.environ:
    sys.path.append(os.path.join(os.environ['SUMO_HOME'], 'tools'))
else:
    sys.exit("Erreur: Déclarez la variable SUMO_HOME")

async def run_sumo_logic(websocket):
    print("🌐 Dashboard connecté")
    
    # --- VARIABLES D'ÉTAT ---
    current_scenario = "normal"
    restart_needed = True  # Pour lancer SUMO dès la connexion
    
    def start_sumo(scenario):
        """Lance ou relance SUMO avec le bon scénario"""
        # 1. FERMER SUMO PROPREMENT
        try:
            print("🛑 Fermeture de SUMO...")
            traci.close()
            import time
            time.sleep(1) # Petit délai pour que Windows libère les fichiers .xml
        except:
            pass
        
        # 2. RÉGÉNÉRER LES FICHIERS
        print(f"🔄 Régénération pour le scénario : {scenario}")
        try:
            subprocess.run([sys.executable, "generer_simulation.py", scenario], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur lors de la génération : {e}")
            return []

        # 3. DÉMARRER SUMO
        is_docker = os.path.exists('/.dockerenv')
        sumo_binary = "sumo" if is_docker else "sumo-gui"
        
        # Astuce : on ajoute --no-internal-links pour éviter d'autres verrous
        traci.start([sumo_binary, "-c", "simulation.sumocfg", "--start", "--quit-on-end"])
        
        return traci.trafficlight.getIDList()

    traffic_lights = []
    step = 0

    try:
        while True:
            # 1. GESTION DU REDÉMARRAGE
            if restart_needed:
                traffic_lights = start_sumo(current_scenario)
                step = 0
                restart_needed = False

            # 2. GESTION DES MESSAGES (Non-bloquant)
            # On vérifie si le Dashboard a envoyé un nouveau scénario
            try:
                # On attend 0.01s max pour ne pas bloquer la simulation
                message = await asyncio.wait_for(websocket.recv(), timeout=0.01)
                data = json.loads(message)
                
                if data.get("action") == "trigger_scenario":
                    current_scenario = data.get("value") or data.get("scenario")
                    print(f"📡 Changement vers : {current_scenario}")
                    restart_needed = True
                    continue # On repart au début de la boucle pour redémarrer
            except asyncio.TimeoutError:
                pass # Pas de message, on continue la simulation
            except websockets.exceptions.ConnectionClosed:
                break

            # 3. LOGIQUE DE SIMULATION
            try:
                traci.simulationStep()
                
                # Collecte des données
                stats = {}
                for tls_id in traffic_lights:
                    # On s'assure que tls_id est bien une string
                    controlled_lanes = traci.trafficlight.getControlledLanes(str(tls_id))
                    lanes = list(set(controlled_lanes))
                    
                    # On récupère la phase et on force le type int
                    current_phase = traci.trafficlight.getPhase(str(tls_id))
                    
                    carrefour_data = {
                        "total_attente": 0,
                        "bras": {},
                        "phase": int(current_phase) if not isinstance(current_phase, tuple) else int(current_phase[0])
                    }

                    for l in lanes:
                        # On force la conversion pour éviter l'erreur Pylance sur 'nb_stop'
                        nb_stop = traci.lane.getLastStepHaltingNumber(str(l))
                        
                        # Sécurité : si SUMO renvoie un tuple au lieu d'un nombre
                        if isinstance(nb_stop, tuple):
                            count = int(nb_stop[0])
                        else:
                            count = int(nb_stop)
                            
                        carrefour_data["bras"][str(l)] = count
                        carrefour_data["total_attente"] += count
                    
                    stats[str(tls_id)] = carrefour_data

                # Envoi au Dashboard
                await websocket.send(json.dumps({
                    "step": step, 
                    "data": stats, 
                    "scenario": current_scenario
                }))
                
                step += 1
                await asyncio.sleep(0.05)

            except Exception as e:
                # Si traci.exceptions n'est pas reconnu, on attrape l'erreur générale
                if "FatalTraCIError" in str(e) or "connection closed" in str(e).lower():
                    print("🏁 Fin de simulation ou SUMO fermé.")
                    await asyncio.sleep(1)
                else:
                    print(f"⚠️ Erreur simulation : {e}")
                    await asyncio.sleep(1)

    finally:
        try: traci.close()
        except: pass

async def main():
    # Écoute sur 0.0.0.0 pour Docker, localhost pour Windows
    host = "0.0.0.0" if os.path.exists('/.dockerenv') else "localhost"
    print(f"🚀 Serveur prêt sur ws://{host}:8765")
    async with websockets.serve(run_sumo_logic, host, 8765, ping_interval=None):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Serveur arrêté.")