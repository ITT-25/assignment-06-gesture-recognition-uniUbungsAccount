[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/HqZjtAXJ)



# 1$ Recognizer, Pointing-input, LSTM Classifier VS 1$ Comparison, Gesture Detection Game 

1. `recognizer.py`, basierend auf Wobbrocks 1$ recognizer, hat ein GUI auf dem 5 Gestures erkannt werden können (Rectangle, Circle, Delete, Check, Pigtail). Es gibt auch den confidence-score.

2. `pointing_input.py` erweitert recongizer.py und erlaubt über die Kamera mit dem Finger zu malen. Dazu kann die Maus oder Leertaste gedrückt werden. Mit Q kann man das Programm beenden und mit S die aktuelle Gesture speichern. Ein Datensatz mit 5x10 Gesten wurde aufgenommen.

3. LSTM classifier wurde trainiert mit eigenem Mid-Air-Datensatz und auf Wobbrocks Datensatz. Dann wurden die 2 classifier jeweils verglichen mit 1$ recognizer. Die Resultate wurden mit Signifikanztest verglichen und im Code dokumentiert.  

4. `gesture_application.py` Ein Earth-Defender Spiel wurde entwickelt, bei dem mit Gesten Kometen zerstört werden müssen. Soundeffekte stammen von https://opengameart.org/content/9-explosion-sounds und https://opengameart.org/content/battle-in-the-winter , Grafiken sind selbst in Photoshop erstellt.

## Installation

Zunächst Git-Repo clonen/runterladen, dann:

1. **Virtuelle Umgebung erstellen und aktivieren**
    ```
    python -m venv venv
    # Windows:
    venv\Scripts\activate
    ```

2. **Abhängigkeiten installieren**
    ```
    pip install -r requirements.txt
    ```

## Starten


1. in cmd im Ordner: `python recognizer.py`
2. in cmd im Ordner: `python pointing_input.py` -> Q to Quit, S to Save, Mouse or Space zum Zeichnen
3. Ausführen optional (sehr lange trainings-Zeit!), jupyter-notebook ist pre-compiled
4. in cmd im Ordner: `python gesture_game.py` -> Gleiche Steuerung wie pointing_input.py

