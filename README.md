# Python Circuit Simulator

A robust, GUI-based desktop application developed in Python that simulates electrical circuits from SPICE-like text netlists. The application performs both time-domain (transient) analysis for linear RLC circuits and iterative DC analysis for non-linear diode circuits.

## Features

* **Interactive PyQt6 GUI:** A modern, semi-transparent user interface featuring a dedicated netlist editor, a real-time simulation output log, and a convenient "Clear All" workspace reset function.
* **Custom Netlist Parsing:** Reads standard engineering netlist inputs either typed directly into the editor or uploaded via a `.txt` file. Supports standard unit suffixes (k, M, m, u, n, p).
* **RLC Transient Analysis:** Utilizes SymPy to construct and solve s-domain matrices via Inverse Laplace Transforms, providing exact time-domain equations for circuits containing Resistors, Inductors, and Capacitors.
* **Iterative DC Analysis:** Implements numerical methods to solve non-linear diode circuits, dynamically computing convergence for node voltages, source currents, and diode states (ON/OFF).

## Technologies Used

* **Python 3**
* **PyQt6:** For the Graphical User Interface and event handling.
* **SymPy:** For symbolic mathematics, matrix operations (`LUsolve`), and Laplace transformations.

## Installation

1. Clone this repository to your local machine:
   '''bash
git clone [https://github.com/Ar-Kal/circuit-simulator-pyqt.git](https://github.com/Ar-Kal/circuit-simulator-pyqt.git)
2. Install the required dependencies:
  pip install PyQt6 sympy
3 . Run the Application:
  python circuit_simulator.py
4. Inputting a Netlist: Choose to either upload a .txt file containing your netlist or manually enter the components using the Component Toolbar.
5. Important Netlist Rules:

    One component per line.

    Node 0 is strictly defined as the ground node. The simulation will warn you if it is missing.

    Node 1 is the positive (+) terminal; Node 2 is the negative (-) terminal.

Click Run Simulation to view the calculated node voltages and equations in the output log.
