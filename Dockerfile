FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Installation de SUMO et des outils nécessaires
RUN apt-get update && apt-get install -y \
    sumo \
    sumo-tools \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# CONFIGURATION CRUCIALE POUR L'INGÉNIEUR CLOUD :
# On définit où se trouve SUMO
ENV SUMO_HOME=/usr/share/sumo
# On dit à Python d'aller chercher les modules (traci, sumolib) dans les outils de SUMO
ENV PYTHONPATH=/usr/share/sumo/tools

RUN pip3 install websockets asyncio

WORKDIR /app
COPY . /app

EXPOSE 8765

CMD ["python3", "controle_Traci.py"]