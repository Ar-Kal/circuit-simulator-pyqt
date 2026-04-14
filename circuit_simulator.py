import sys
import math

# --- SymPy Imports (from backend) ---
from sympy import symbols, Matrix, simplify, apart, Heaviside
from sympy.integrals.transforms import inverse_laplace_transform

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QTextEdit, QPushButton, QSplitter, QLabel, QFrame,
    QDialog, QLineEdit, QFormLayout, QDialogButtonBox,
    QFileDialog, QStackedWidget
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

# --- Helper Dictionaries ---
COMP_DETAILS = {
    'R': "Resistance (Ω)", 'C': "Capacitance (F)", 'L': "Inductance (H)",
    'V': "Voltage (V)", 'I': "Current (A)", 'D': "Model" # 'D' is now just a key
}
COMP_NAME_MAP = {
    'R': "Resistor", 'C': "Capacitor", 'L': "Inductor",
    'V': "Voltage Source", 'I': "Current Source", 'D': "Diode"
}


class ComponentDialog(QDialog):
    """ A pop-up dialog to get component details from the user. """
    def __init__(self, comp_type, parent=None):
        super().__init__(parent)
        comp_name = f"Add {COMP_NAME_MAP.get(comp_type, 'Component')}"
        self.setWindowTitle(comp_name)
        self.form_layout = QFormLayout()
        main_layout = QVBoxLayout(self)
        
        self.full_name_edit = QLineEdit(f"{comp_type}?") 
        self.node1_edit = QLineEdit("1")
        self.node2_edit = QLineEdit("0")
        self.value_edit = QLineEdit() # This will be hidden for Diodes
        
        self.form_layout.addRow("Full Name:", self.full_name_edit)
        self.form_layout.addRow("Node 1:", self.node1_edit)
        self.form_layout.addRow("Node 2:", self.node2_edit)
        
        # --- MODIFIED LOGIC ---
        if comp_type == 'D':
            fixed_model_label = QLabel("<b>Fixed Model</b> (Vth=0.7V, R_on=1mΩ)")
            fixed_model_label.setStyleSheet("color: #333;")
            self.form_layout.addRow("Model:", fixed_model_label)
            self.value_edit.setText("") 
            self.value_edit.setVisible(False)
        
        elif comp_type in COMP_DETAILS:
            # For all other components
             self.form_layout.addRow(f"{COMP_DETAILS[comp_type]}:", self.value_edit)
             if comp_type == 'V' or comp_type == 'I':
                 self.value_edit.setPlaceholderText("e.g., 10 or 5m")
             elif comp_type == 'R':
                 self.value_edit.setPlaceholderText("e.g., 100 or 1k")
        # --- END MODIFIED LOGIC ---

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        main_layout.addLayout(self.form_layout)
        main_layout.addWidget(button_box)
        self.setLayout(main_layout)

    def get_data(self):
        # This function is unchanged and works correctly
        return (self.full_name_edit.text(), self.node1_edit.text(), self.node2_edit.text(), self.value_edit.text())


class MainWindow(QMainWindow):
    """ Main application window """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Circuit Simulator")
        self.setGeometry(100, 100, 1000, 700) 
        self.setObjectName("MainWindow") # This ID is used by the stylesheet

        # --- Main Layout ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- Left Panel is a QStackedWidget ---
        self.left_stack = QStackedWidget()
        choice_page = self.create_choice_page()
        manual_entry_page = self.create_manual_entry_page()
        self.left_stack.addWidget(choice_page)     # Page Index 0
        self.left_stack.addWidget(manual_entry_page) # Page Index 1
        splitter.addWidget(self.left_stack)
        self.left_stack.setCurrentIndex(0)

        # --- Right Panel (Controls & Output) ---
        right_panel = QFrame()
        right_panel.setObjectName("RightPanelFrame") 
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        self.run_button = QPushButton("▶ Run Simulation")
        self.run_button.setFont(QFont("Inter", 11, QFont.Weight.Bold))
        self.run_button.setMinimumHeight(40)
        self.run_button.clicked.connect(self.run_simulation)
        right_layout.addWidget(self.run_button)
        
        # --- "Clear All" Button Added ---
        self.clear_all_button = QPushButton("Clear All")
        self.clear_all_button.setObjectName("ClearButton") # For styling
        self.clear_all_button.setMinimumHeight(30)
        self.clear_all_button.clicked.connect(self.clear_all)
        right_layout.addWidget(self.clear_all_button)
        
        right_layout.addSpacing(10) # Add space before output label
        
        output_label = QLabel("Simulation Output")
        output_label.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        right_layout.addWidget(output_label)
        
        self.output_log = QTextEdit()
        self.output_log.setFont(QFont("Courier New", 11))
        self.output_log.setReadOnly(True)
        self.output_log.setPlaceholderText("Simulation results will appear here...")
        right_layout.addWidget(self.output_log)
        
        splitter.addWidget(right_panel)
        
        # --- Final Window Setup ---
        splitter.setSizes([500, 500]) 
        self.setCentralWidget(splitter)

    # --- Choice Page (Page 0) ---
    def create_choice_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("Add a Netlist")
        title.setFont(QFont("Inter", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("How do you want to start?")
        subtitle.setFont(QFont("Inter", 11))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # --- INFORMATION BLOCK ---
        info_text = (
            "<b><u>Necessary Information</u></b><br><br>"
            "<b>Rules:</b>"
            "<ul>"
            "<li><b>One Component Per Line</b> (e.g., R1 1 0 1k)</li>"
            "<li><b>Nodes Must Be Numbers</b> (e.g., 1, 2, 0). '0' is ground.</li>"
            "<li><b>Node 1</b> is the positive (+) terminal.</li>"
            "<li><b>Node 2</b> is the negative (-) terminal.</li>"
            "</ul>"
            "<b>Suffixes:</b><br>"
            "<b>G</b>: Giga | <b>M</b>: Mega | <b>k</b>: kilo | <b>m</b>: milli<br>"
            "<b>u</b>: micro | <b>n</b>: nano | <b>p</b>: pico | <b>f</b>: femto"
        )
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setStyleSheet(
            "font-size: 9pt; color: #495057; background-color: #e9ecef; "
            "border: 1px solid #dee2e6; border-radius: 10px; padding: 12px;"
        )
        info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(info_label)

        layout.addSpacing(20)
        
        self.manual_entry_button = QPushButton("Enter Input Manually")
        self.manual_entry_button.setObjectName("ChoiceButton")
        self.manual_entry_button.setMinimumHeight(60)
        self.manual_entry_button.clicked.connect(self.go_to_manual_page)
        layout.addWidget(self.manual_entry_button)
        
        or_label = QLabel("OR")
        or_label.setFont(QFont("Inter", 10, QFont.Weight.Bold))
        or_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(or_label)
        
        self.upload_file_button = QPushButton("Upload a .txt File")
        self.upload_file_button.setObjectName("ChoiceButton")
        self.upload_file_button.setMinimumHeight(60)
        self.upload_file_button.clicked.connect(self.go_to_upload_page)
        layout.addWidget(self.upload_file_button)
        
        layout.addStretch()
        return page

    # --- Manual Entry Page (Page 1) ---
    def create_manual_entry_page(self):
        page = QWidget()
        left_layout = QVBoxLayout(page)

        self.back_button = QPushButton("« Back to Options")
        self.back_button.setObjectName("BackButton")
        self.back_button.clicked.connect(self.go_to_choice_page)
        left_layout.addWidget(self.back_button)
        
        # --- Component Toolbar ---
        comp_toolbar_label = QLabel("Component Toolbar")
        comp_toolbar_label.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        left_layout.addWidget(comp_toolbar_label)
        
        comp_toolbar_layout = QHBoxLayout()
        self.add_v_button = QPushButton("V Source")
        self.add_i_button = QPushButton("I Source")
        self.add_r_button = QPushButton("Resistor")
        self.add_c_button = QPushButton("Capacitor")
        self.add_l_button = QPushButton("Inductor")
        self.add_d_button = QPushButton("Diode")
        
        for button in [self.add_v_button, self.add_i_button, self.add_r_button, 
                       self.add_c_button, self.add_l_button, self.add_d_button]:
            button.setObjectName("ToolbarButton")

        comp_toolbar_layout.addWidget(self.add_v_button)
        comp_toolbar_layout.addWidget(self.add_i_button)
        comp_toolbar_layout.addWidget(self.add_r_button)
        comp_toolbar_layout.addWidget(self.add_c_button)
        comp_toolbar_layout.addWidget(self.add_l_button)
        comp_toolbar_layout.addWidget(self.add_d_button)
        comp_toolbar_layout.addStretch()
        left_layout.addLayout(comp_toolbar_layout)
        
        # Connect buttons
        self.add_v_button.clicked.connect(lambda: self.open_add_component_dialog('V'))
        self.add_i_button.clicked.connect(lambda: self.open_add_component_dialog('I'))
        self.add_r_button.clicked.connect(lambda: self.open_add_component_dialog('R'))
        self.add_c_button.clicked.connect(lambda: self.open_add_component_dialog('C'))
        self.add_l_button.clicked.connect(lambda: self.open_add_component_dialog('L'))
        self.add_d_button.clicked.connect(lambda: self.open_add_component_dialog('D'))

        # --- Netlist Editor ---
        editor_label = QLabel("Netlist Editor")
        editor_label.setFont(QFont("Inter", 12, QFont.Weight.Bold))
        left_layout.addWidget(editor_label)
        
        self.netlist_editor = QTextEdit()
        self.netlist_editor.setFont(QFont("Courier New", 11))
        self.netlist_editor.setPlaceholderText(
            "* Example: DC Diode Circuit\n"
            "V1 1 0 10\n"
            "R1 1 2 1k\n"
            "D1 2 0\n"
            "\n* Example: RLC Transient Circuit\n"
            "* V2 1 0 5\n"
            "* R2 1 2 100\n"
            "* L1 2 0 1m\n"
            "* I1 2 0 1m\n"
        )
        left_layout.addWidget(self.netlist_editor)
        
        return page

    # --- Navigation Functions ---
    def go_to_manual_page(self):
        self.new_netlist()
        self.left_stack.setCurrentIndex(1)
        
    def go_to_upload_page(self):
        if self.open_netlist_file():
            self.left_stack.setCurrentIndex(1)
            
    def go_to_choice_page(self):
        self.left_stack.setCurrentIndex(0)

    # --- File/Editor Functions ---
    def new_netlist(self):
        self.netlist_editor.clear()
        self.output_log.append("[INFO] Netlist cleared for new manual entry.")

    def clear_all(self):
        """ Clears both the input and output text areas. """
        self.netlist_editor.clear()
        self.output_log.clear()

    def open_netlist_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Netlist File", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    file_content = f.read()
                self.netlist_editor.setText(file_content)
                self.output_log.append(f"[INFO] Successfully loaded netlist from: {file_path}")
                return True
            except Exception as e:
                self.output_log.append(f"[ERROR] Failed to read file: {str(e)}")
                return False
        return False

    def open_add_component_dialog(self, comp_type):
        """ Opens the ComponentDialog to get user input. """
        dialog = ComponentDialog(comp_type, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            
            full_name, n1, n2, value = dialog.get_data()
            
            if full_name and n1 and n2:
                line = f"{full_name} {n1} {n2} {value}".strip()
                self.netlist_editor.append(line)
            else:
                self.output_log.append("[INFO] Component add cancelled (empty fields).")


    def parse_value(self, val):
        """ Parses a string value with suffixes (k, M, m, u, n, p). """
        val = str(val).strip()
        suffixes = {'f':1e-15, 'p':1e-12, 'n':1e-9, 'u':1e-6, 'U':1e-6, 
                    'm':1e-3, 'k':1e3, 'K':1e3, 'M':1e6, 'meg':1e6, 'G':1e9}
        for s,f in suffixes.items():
            if val.endswith(s):
                try:
                    return float(val[:-len(s)]) * f
                except ValueError:
                    pass 
        try:
            return float(val)
        except ValueError:
            try:
                # Try to evaluate simple math expressions
                return float(eval(val, {"__builtins__": None, "math": math}))
            except Exception:
                raise ValueError(f"Cannot parse value: {val}")

    def parse_netlist_text(self, netlist_string):
        """
        Parses the netlist text from the QPlainTextEdit widget.
        """
        components = []
        
        for line_number, line in enumerate(netlist_string.splitlines(), 1):
            try:
                line = line.strip()
                
                if line.startswith('*') or not line:
                    continue
                
                if '*' in line:
                    line = line.split('*')[0].strip()
                
                tokens = line.split()
                
                if len(tokens) < 3:
                    self.output_log.append(f" Skipping line {line_number} (too few tokens): {line}")
                    continue
                
                component_name = tokens[0]
                node1 = tokens[1]
                node2 = tokens[2]
                value = "" # Default value if only 3 tokens
                
                if len(tokens) > 3:
                    value = " ".join(tokens[3:]) # Join all remaining tokens for value/model
                
                component_type = component_name[0].upper()
                
                if component_type not in COMP_NAME_MAP:
                    self.output_log.append(f" Skipping line {line_number} (Unknown type '{component_type}'): {line}")
                    continue

                component_data = {
                    'full_name' : component_name,
                    'name' : component_type,
                    'node_1' : node1,
                    'node_2' : node2,
                    'value' : value,
                    'line': line_number # For error reporting
                }
                components.append(component_data)
                
            except Exception as e:
                self.output_log.append(f" Failed to parse line {line_number}: {line}. Error: {e}")
        
        return components

    def run_simulation(self):
        """ 
        This is the main function where the backend logic is integrated.
        """
        netlist_text = self.netlist_editor.toPlainText()
        self.output_log.clear()
        
        # --- Main Try/Except Block to catch all simulation errors ---
        try:
            self.output_log.append("--- Simulation Started ---")
            
            # 1. PARSE NETLIST
            comp = self.parse_netlist_text(netlist_text)
            if not comp:
                self.output_log.append(" Netlist is empty or could not be parsed.")
                self.output_log.append("Simulation Aborted ")
                return

            self.output_log.append(f" Parsed {len(comp)} components.")

            # 2. FIND MAX NODE & COMPONENT COUNTS
            max_node = 0
            ind_source = 0 # Voltage sources
            diode_source = 0
            diodes = []
            v_sources = []
            all_nodes = set()

            for data in comp:
                try:
                    # --- CRITICAL: Check nodes are integers, per backend requirement ---
                    n1_int = int(data['node_1'])
                    n2_int = int(data['node_2'])
                    all_nodes.add(n1_int)
                    all_nodes.add(n2_int)
                except ValueError:
                    self.output_log.append(f" Invalid node in line {data['line']}: {data['full_name']}. Nodes must be integers (e.g., '1', '2', '0').")
                    self.output_log.append("--- Simulation Aborted ")
                    return
            
            if not all_nodes:
                self.output_log.append(" No nodes found in netlist.")
                self.output_log.append("--- Simulation Aborted ")
                return
            
            if 0 not in all_nodes:
                 self.output_log.append(" No ground node '0' found. This may lead to an unsolvable (singular) matrix.")
            
            max_node = max(all_nodes)
            
            for data in comp:
                if data['name'] == 'V':
                    ind_source += 1
                    v_sources.append(data)
                if data['name'] == 'D':
                    diode_source += 1
                    diodes.append(data)
            
            self.output_log.append(f" Max node: {max_node}, V-Sources: {ind_source}, Diodes: {diode_source}")

            # 3. SELECT ANALYSIS TYPE
            
            # --- RLC CIRCUIT (s-Domain Analysis) ---
            if diode_source == 0:
                self.output_log.append(" No diodes found. Running RLC/Transient (s-domain) analysis")
                s = symbols('s')
                t = symbols('t', real=True, positive=True)
                
                matrix_size = max_node + ind_source
                if matrix_size == 0:
                    self.output_log.append(" No nodes or sources found for RLC analysis.")
                    return
                    
                Z = Matrix.zeros(matrix_size, 1)
                A = Matrix.zeros(matrix_size, matrix_size)
                
                vs_index = 0
                for data in comp:
                    n1 = int(data['node_1'])
                    n2 = int(data['node_2'])
                    Y = 0 # Admittance

                    try:
                        if data['name'] == 'R':
                            Y = 1 / self.parse_value(data['value'])
                        elif data['name'] == 'L':
                            Y = 1 / (s * self.parse_value(data['value']))
                        elif data['name'] == 'C':
                            Y = s * self.parse_value(data['value'])
                    except Exception as e:
                        self.output_log.append(f"Invalid value for {data['full_name']} on line {data['line']}: {e}")
                        return

                    if data['name'] in ['R', 'L', 'C']:
                        if n1 == 0:
                            if n2 > 0: A[n2-1, n2-1] += Y
                        elif n2 == 0:
                            if n1 > 0: A[n1-1, n1-1] += Y
                        elif n1 > 0 and n2 > 0:
                            A[n1-1, n2-1] -= Y
                            A[n2-1, n1-1] -= Y
                            A[n1-1, n1-1] += Y
                            A[n2-1, n2-1] += Y

                    elif data['name'] == 'V':
                        aux_index = max_node + vs_index
                        if n1 != 0:
                            A[n1-1, aux_index] += 1
                            A[aux_index, n1-1] += 1
                        if n2 != 0:
                            A[n2-1, aux_index] -= 1
                            A[aux_index, n2-1] -= 1
                        vs_index += 1
                
                # --- Fill Z (I) vector ---
                vs_index = 0
                for data in comp:
                    try:
                        if data['name'] == 'I':
                            n1 = int(data['node_1'])
                            n2 = int(data['node_2'])
                            value = self.parse_value(data['value'])
                            # Assuming DC value, so Laplace transform is value/s
                            if n1 != 0: Z[n1-1, 0] -= value / s
                            if n2 != 0: Z[n2-1, 0] += value / s
                        
                        elif data['name'] == 'V':
                            value = self.parse_value(data['value'])
                            # Assuming DC value, so Laplace transform is value/s
                            Z[max_node + vs_index, 0] += value / s
                            vs_index += 1
                    except Exception as e:
                        self.output_log.append(f" Invalid value for {data['full_name']} on line {data['line']}: {e}")
                        return

                # --- Solve Matrix ---
                self.output_log.append(" Solving s-domain matrix A*X = Z")
                X = A.LUsolve(Z)
                self.output_log.append(" Solution found. ")

                self.output_log.append("\n--- Simulation Results (Time-Domain) ")
                for i in range(matrix_size):
                    X_s = X[i, 0]
                    X_t_final_str = ""
                    try:
                        if X_s == 0:
                            X_t_final_str = "0"
                        else:
                            X_s_simplified = simplify(X_s)
                            X_s_apart = apart(X_s_simplified, s)
                            X_t = inverse_laplace_transform(X_s_apart, s, t, doit=True, noconds=True)
                            X_t_final = X_t * Heaviside(t)
                            X_t_final_str = str(X_t_final)
                    except Exception as e:
                        X_t_final_str = f" Could not compute Inverse Laplace Transform for {X_s}: {e}"

                    if i < max_node:
                        self.output_log.append(f"V({i+1})(t) = {X_t_final_str}")
                    else:
                        vs_name = v_sources[i - max_node]['full_name']
                        self.output_log.append(f"I({vs_name})(t) = {X_t_final_str}")

            # --- RESISTOR-DIODE CIRCUIT (DC Iterative Analysis) ---
            else:
                self.output_log.append("Diodes detected. Running iterative DC analysis...")
                MAX_ITERATIONS = 50
                Vth = 0.7
                R_on = 1e-3
                R_off = 1e9
                G_on = 1 / R_on
                G_off = 1 / G_off
                
                diode_states = {d['full_name']: False for d in diodes} # Start all OFF
                X_prev = None
                matrix_size = max_node + ind_source
                
                if matrix_size == 0:
                    self.output_log.append(" No nodes or sources found for Diode analysis.")
                    return
                    
                a_map = {}
                current_a_ind = max_node
                for data in v_sources:
                    a_map[data['full_name']] = current_a_ind
                    current_a_ind += 1
                
                X = None # Ensure X is defined
                iteration = 0
                
                for iteration in range(MAX_ITERATIONS):
                    
                    A = Matrix.zeros(matrix_size, matrix_size)
                    Z = Matrix.zeros(matrix_size, 1)
                    
                    for data in comp:
                        n1 = int(data['node_1'])
                        n2 = int(data['node_2'])
                        value = 0
                        try:
                            # Only parse value for components that use it in DC
                            if data['name'] in ['R', 'I', 'V']:
                                value = self.parse_value(data['value'])
                        except ValueError as e:
                            self.output_log.append(f" Bad value for {data['full_name']} on line {data['line']}: {e}")
                            return
                        
                        name = data['name']
                        
                        if name == 'R':
                            G = 1 / value
                            if n1 != 0:
                                A[n1 - 1, n1 - 1] += G
                                if n2 != 0: A[n1 - 1, n2 - 1] -= G
                            if n2 != 0:
                                A[n2 - 1, n2 - 1] += G
                                if n1 != 0: A[n2 - 1, n1 - 1] -= G
                        
                        elif name == 'I':
                            if n1 != 0: Z[n1 - 1, 0] -= value
                            if n2 != 0: Z[n2 - 1, 0] += value
                        
                        elif name == 'V':
                            aux_index = a_map[data['full_name']]
                            if n1 != 0:
                                A[n1 - 1, aux_index] += 1
                                A[aux_index, n1 - 1] += 1
                            if n2 != 0:
                                A[n2 - 1, aux_index] -= 1
                                A[aux_index, n2 - 1] -= 1
                            Z[aux_index, 0] = value
                        
                        elif name == 'D':
                            # NOTE: data['value'] is ignored, fixed model is used
                            state = diode_states[data['full_name']]
                            
                            if state: # Diode is ON
                                G = G_on
                                I_eq = Vth * G
                                if n1 != 0: Z[n1 - 1, 0] += I_eq
                                if n2 != 0: Z[n2 - 1, 0] -= I_eq
                            else: # Diode is OFF
                                G = G_off
                            
                            # Add conductance for both states
                            if n1 != 0:
                                A[n1 - 1, n1 - 1] += G
                                if n2 != 0: A[n1 - 1, n2 - 1] -= G
                            if n2 != 0:
                                A[n2 - 1, n2 - 1] += G
                                if n1 != 0: A[n2 - 1, n1 - 1] -= G

                    try:
                        X = A.LUsolve(Z)
                    except Exception:
                        self.output_log.append(" Singular Matrix. Circuit may be unsolvable (e.g., floating nodes or V-source loop).")
                        break 

                    if X is None: break

                    states_changed = False
                    new_diode_states = diode_states.copy()

                    for d in diodes:
                        d_name = d['full_name']
                        n1 = int(d['node_1'])
                        n2 = int(d['node_2'])
                        
                        Va = X[n1 - 1, 0] if n1 != 0 else 0
                        Vc = X[n2 - 1, 0] if n2 != 0 else 0
                        Vd_calc = Va - Vc
                        
                        current_state = diode_states[d_name]

                        if not current_state and Vd_calc > Vth:
                            new_diode_states[d_name] = True
                            states_changed = True
                        
                        elif current_state:
                            Id_calc = (Vd_calc - Vth) / R_on
                            if Id_calc < -1e-9: # Check if current is negative
                                new_diode_states[d_name] = False
                                states_changed = True

                    diode_states = new_diode_states

                    # Check for convergence
                    delta_norm = 0.0
                    if X_prev is not None:
                        delta = (X - X_prev)
                        delta_norm = delta.norm()
                        
                    if not states_changed and X_prev is not None and delta_norm < 1e-6:
                        self.output_log.append(f" Converged after {iteration + 1} iterations.")
                        break
                    
                    X_prev = X.copy()
                
                if iteration == MAX_ITERATIONS - 1:
                    self.output_log.append(" Maximum iterations reached. Solution may not have converged.")

                if X is not None:
                    self.output_log.append("\n--- Simulation Results (DC) ---")
                    self.output_log.append("--- Node Voltages ---")
                    for i in range(max_node):
                        self.output_log.append(f"V({i + 1}) = {X[i, 0]:.4f} V")
                    
                    self.output_log.append("\n--- Source Currents ---")
                    for vs_name, aux_index in a_map.items():
                        if aux_index < X.rows:
                            self.output_log.append(f"I({vs_name}) = {-1*X[aux_index, 0]:.4e} A")

                    self.output_log.append("\n--- Diode States ---")
                    for d in diodes:
                        d_name = d['full_name']
                        n1, n2 = int(d['node_1']), int(d['node_2'])
                        V1 = X[n1 - 1, 0] if n1 != 0 else 0
                        V2 = X[n2 - 1, 0] if n2 != 0 else 0
                        Vd_calc = V1 - V2
                        is_on = diode_states[d_name]
                        
                        if is_on:
                            Id_calc = (Vd_calc - Vth) / R_on
                            status = "ON"
                        else:
                            Id_calc = Vd_calc / R_off
                            status = "OFF"
                        
                        self.output_log.append(f"{d_name}: Status={status}, VD={Vd_calc:.4f}V, ID={Id_calc:.4e}A")
            
            self.output_log.append("\n--- Simulation Finished ---")

        except Exception as e:
            self.output_log.append(f"\n--- UNEXPECTED SIMULATION ERROR ---")
            self.output_log.append(f"An error occurred: {str(e)}")
            import traceback
            self.output_log.append(f"\nTraceback:\n{traceback.format_exc()}")
            

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # --- Stylesheet ---
    app.setStyleSheet("""
        /* --- Global Settings --- */
        QWidget {
            font-family: "Inter", "Segoe UI", sans-serif;
            font-size: 10pt;
            color: #212529; /* Dark text */
        }

        /* --- Main Window Background --- */
        /* This targets the main window using its object name */
        /* The image MUST be in the same folder as the script */
        QMainWindow#MainWindow {
            /* * Use border-image to stretch the background.
             * This is the correct Qt property instead of 'background-size'.
             * It stretches the image to fill the entire widget.
             */
            border-image: url(istockphoto-532350072-612x612.jpg) 0 0 0 0 stretch stretch;
        }
        
        /* --- Dialogs --- */
        QDialog {
            /* Semi-transparent so bg shows through a bit */
            background-color: rgba(255, 255, 255, 0.95); 
        }
        
        /* --- Left Panel (QStackedWidget) --- */
        /* Make the pages semi-transparent */
        QStackedWidget > QWidget {
             background-color: rgba(255, 255, 255, 0.92); /* 92% Opaque White */
             border-radius: 10px;
        }

        /* --- Right Panel --- */
        /* Make the right frame semi-transparent */
        QFrame#RightPanelFrame {
            background-color: rgba(248, 249, 250, 0.92); /* 92% Opaque Light Grey */
            border-radius: 10px;
            border: none;
        }

        /* --- Text Editors --- */
        QTextEdit {
            background-color: rgba(255, 255, 255, 0.8); /* More transparent */
            border: 1px solid #dee2e6;
            border-radius: 10px; /* Rounded corners */
            padding: 8px;
            font-family: "Courier New", monospace;
            font-size: 10pt;
            color: #343a40;
        }
        QTextEdit:focus {
            border: 2px solid #007bff; /* Accent on focus */
        }
        
        /* --- Line Edits (in Dialog) --- */
        QLineEdit {
            padding: 8px;
            border: 1px solid #ced4da;
            border-radius: 10px; /* Rounded corners */
            background-color: #ffffff;
        }
        QLineEdit:focus {
            border: 2px solid #007bff;
        }

        /* --- Labels --- */
        QLabel {
            color: #212529; /* Darker text for readability on transparent bg */
            padding-bottom: 2px;
            background-color: none; /* Ensure labels have no bg */
        }
        /* Title labels (like "Add a Netlist", "Component Toolbar") */
        QLabel[font*='Bold'] {
            color: #000;
            font-size: 12pt;
        }
        
        /* --- Splitter --- */
        QSplitter::handle {
            background-color: #e9ecef;
            width: 4px;
        }
        QSplitter::handle:hover {
            background-color: #007bff; /* Blue on hover */
        }

        /* --- === BUTTON STYLING === --- */
        
        /* Base Button Style */
        QPushButton {
            border: none;
            border-radius: 10px; /* Rounded corners */
            padding: 9px 14px;
            font-weight: 500; /* Medium weight */
            font-size: 10pt;
        }
        QPushButton:pressed {
            background-color: #004c8a; /* Darker press */
        }

        /* --- Primary "Run" Button --- */
        QPushButton[text="▶ Run Simulation"] {
            background-color: #007bff; /* Primary Blue */
            color: white;
            font-weight: bold;
            font-size: 11pt;
            padding: 12px 14px;
        }
        QPushButton[text="▶ Run Simulation"]:hover {
            background-color: #0069d9;
        }
        QPushButton[text="▶ Run Simulation"]:pressed {
            background-color: #0056b3;
        }

        /* --- Big "Choice" Buttons --- */
        QPushButton#ChoiceButton {
            font-size: 12pt;
            font-weight: bold;
            background-color: #28a745; /* Green */
            color: white;
            padding: 15px;
        }
        QPushButton#ChoiceButton:hover { background-color: #218838; }
        QPushButton#ChoiceButton:pressed { background-color: #1e7e34; }
        
        /* --- "Back" Button --- */
        QPushButton#BackButton {
            background-color: #6c757d; /* Grey */
            color: white;
            padding: 6px 10px;
            font-size: 9pt;
            font-weight: bold;
            text-align: left;
            max-width: 130px;
        }
        QPushButton#BackButton:hover { background-color: #5a6268; }
        QPushButton#BackButton:pressed { background-color: #495057; }
        
        /* --- "Clear All" Button --- */
        QPushButton#ClearButton {
            background-color: #dc3545; /* Red */
            color: white;
            font-size: 9pt;
            font-weight: bold;
            padding: 8px 10px;
        }
        QPushButton#ClearButton:hover { background-color: #c82333; }
        QPushButton#ClearButton:pressed { background-color: #bd2130; }

        /* --- Component Toolbar Buttons --- */
        QPushButton#ToolbarButton {
            background-color: #e9ecef; /* Light grey */
            color: #343a40;
            padding: 8px 10px;
            font-size: 9pt;
            font-weight: 500;
        }
        QPushButton#ToolbarButton:hover {
            background-color: #d1d5da; /* Darker grey */
        }
        QPushButton#ToolbarButton:pressed {
            background-color: #b8bfc6;
        }
        
        /* --- Dialog Buttons (OK/Cancel) --- */
        QDialogButtonBox QPushButton {
            background-color: #6c757d; /* Grey */
            color: white;
            border-radius: 6px; /* Slightly less round for dialogs */
        }
        QDialogButtonBox QPushButton:hover { background-color: #5a6268; }
        /* Make 'OK' button primary */
        QDialogButtonBox QPushButton[text="OK"] {
             background-color: #007bff; /* Blue */
             color: white;
        }
        QDialogButtonBox QPushButton[text="OK"]:hover {
             background-color: #0069d9;
        }
    """)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec())