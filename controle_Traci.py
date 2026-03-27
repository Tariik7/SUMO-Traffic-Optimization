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
    restart_needed = True  
    incident_declenche = False  
    
    def start_sumo(scenario):
        """Lance ou relance SUMO avec le bon scénario et les paramètres Sublane"""
        try:
            print("🛑 Fermeture de SUMO...")
            traci.close()
            import time
            time.sleep(1) 
        except:
            pass
        
        print(f"🔄 Régénération pour le scénario : {scenario}")
        try:
            subprocess.run([sys.executable, "generer_simulation.py", scenario], check=True)
        except subprocess.CalledProcessError as e:
            print(f"❌ Erreur lors de la génération : {e}")
            return []

        is_docker = os.path.exists('/.dockerenv')
        sumo_binary = "sumo" if is_docker else "sumo-gui"
        
        # Lancement avec Sublane Model activé (résolution fine pour dépassement)
        traci.start([
            sumo_binary, "-c", "simulation.sumocfg", 
            "--start", "--quit-on-end",
            "--lateral-resolution", "0.2",
            "--gui-settings-file", "vue.view.xml"  # <--- Force le fichier de vue ici
    ])     
        
        # --- CONFIGURATION DES COMPORTEMENTS DE DÉPASSEMENT ---
        # On rend les véhicules plus enclins à doubler l'accident
        for vtype in traci.vehicletype.getIDList():
            traci.vehicletype.setParameter(vtype, "lcPushy", "1.0")
            traci.vehicletype.setParameter(vtype, "lcAssertive", "1.5")
            traci.vehicletype.setParameter(vtype, "lcLatential", "1.0")
            traci.vehicletype.setMinGapLat(vtype, 0.2)
            traci.vehicletype.setMaxSpeedLat(vtype, 1.0)
        
        return traci.trafficlight.getIDList()

    traffic_lights = []
    step = 0

    try:
        while True:
            if restart_needed:
                print(f"DEBUG: Lancement de start_sumo avec {current_scenario}")
                traffic_lights = start_sumo(current_scenario)
                step = 0
                restart_needed = False
                incident_declenche = False

            # --- RÉCEPTION MESSAGE ---
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=0.01)
                data = json.loads(message)
                if data.get("action") == "trigger_scenario":
                    current_scenario = data.get("value") or data.get("scenario")
                    restart_needed = True
                    continue
            except asyncio.TimeoutError:
                pass

            # --- SIMULATION ---
            try:
                traci.simulationStep()
                
                # --- LOGIQUE ACCIDENT ---
                if current_scenario == "incident" and not incident_declenche and step > 50:
                    veh_list = traci.vehicle.getIDList()
                    if len(veh_list) > 0:
                        victim_id = veh_list[0]
                        try:
                            lane_id = traci.vehicle.getLaneID(victim_id)
                            pos_actuelle = traci.vehicle.getLanePosition(victim_id)
                            pos_valide = float(pos_actuelle[0]) if isinstance(pos_actuelle, tuple) else float(pos_actuelle)

                            # On donne +30m pour éviter l'erreur "too close to brake"
                            traci.vehicle.setStop(victim_id, traci.vehicle.getRoadID(victim_id), 
                                                 pos=pos_valide + 30, duration=1000)
                            
                            traci.vehicle.setColor(victim_id, (255, 0, 0, 255))
                            traci.vehicle.setSignals(victim_id, 3) 
                            
                            await websocket.send(json.dumps({
                                "type": "notification",
                                "msg": f"⚠️ Accident : {victim_id} immobilisé sur {lane_id}",
                                "timestamp": step
                            }))
                            incident_declenche = True 
                        except Exception as e:
                            print(f"DEBUG: Erreur TRACI accident: {e}")

                # --- ENVOI STATS ---
                stats = {}
                for tls_id in traffic_lights:
                    stats[tls_id] = {"bras": {}, "phase": traci.trafficlight.getPhase(tls_id)}
                    lanes = traci.trafficlight.getControlledLanes(tls_id)
                    for lane_id in list(set(lanes)):
                        raw_val = traci.lane.getLastStepHaltingNumber(lane_id)
                        val_correcte = raw_val[0] if isinstance(raw_val, (tuple, list)) else raw_val
                        halt_num = int(val_correcte)
                        if halt_num > 0:
                            stats[tls_id]["bras"][lane_id] = halt_num

                await websocket.send(json.dumps({
                    "type": "stats",
                    "step": step, 
                    "data": stats, 
                    "scenario": current_scenario
                }))
                
                step += 1
                await asyncio.sleep(0.05)

            except Exception as e:
                print(f"DEBUG: Erreur boucle simulation: {e}")
                break

    finally:
        try: traci.close()
        except: pass

async def main():
    host = "0.0.0.0" if os.path.exists('/.dockerenv') else "localhost"
    print(f"🚀 Serveur prêt sur ws://{host}:8765")
    async with websockets.serve(run_sumo_logic, host, 8765, ping_interval=None):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Serveur arrêté.")