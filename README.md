# ✨ Truss Suite: Numerical Truss Optimizer & Editor ✨

The Truss Suite is an integrated application designed for the analysis, design, and optimization of 2D truss structures using the Finite Element Method (FEM). Built on **PySide6** and leveraging powerful libraries like Pandas and Matplotlib, this suite provides an intuitive graphical interface for structural experimentation.

The application is unified under a single **Launcher** which provides access to three main tools: the **Editor**, the **Optimizer**, and the **Visualizer**.

## 🚀 Easy Usage

The Truss Suite can be launched either from a pre-built executable or directly from the source code.

### 1. From a Release Build (.exe)

This is the simplest way to run the application if a pre-compiled executable is available (e.g., bundled using PyInstaller).

1. **Download:** Obtain the latest compiled executable (e.g., `TrussSuite.exe`) from the project's releases page.
    
2. **Run:** Execute the `TrussSuite.exe` file directly.
    

### 2. From Source Code (Python)

To run the application directly from the source files:

1. **Prerequisites:** Ensure all required Python packages listed in the **Required Packages** section are installed in your environment.
    
2. **Launch:** Run the main application entry point from the `src/` directory:
    
    ```
    python launcher.py
    ```
    

### 3. Workflow Steps

Once the application is running, follow these steps:

1. **Edit:** Use the **Truss Editor** to define your truss geometry, supports, loads, and material properties. All data is saved and loaded using standard CSV files in the `data/` directory.
    
2. **Optimize:** Switch to the **Optimizer** to define objective function weights (e.g., prioritize lightness vs. stiffness) and run the numerical optimization.
    
3. **Visualize:** Use the **Visualizer** or the built-in views to inspect results, view deformed states, and export professional diagrams.
    

## 📂 Project Structure

```
.
├── data/
│   ├── design_1/
│   │   ├── loads.csv
│   │   ├── materials.csv
│   │   ├── points.csv
│   │   ├── supports.csv
│   │   └── trusses.csv
│   ├── design_2/
│   │   └── ...
├── src/
│   ├── launcher.py           # Main application entry point for the suite
│   ├── editor.py             # Contains the Truss Editor application
│   ├── optimizer_app.py      # Contains the Truss Optimizer application
│   ├── visualizer.py         # Contains the Truss Visualizer application
│   ├── fem_solver.py         # Core Finite Element Method (FEM) solver
│   ├── optimizer.py          # Implementation of optimization algorithms
│   ├── truss_model.py        # High-level data structure for the truss
│   ├── analysis.py           # Functions for objective calculation and fitness scoring
│   ├── ui_components.py      # Custom Matplotlib canvas and UI elements
│   └── ui_themes.py          # Qt stylesheet definitions (Light/Dark mode)
└── output/
    └── 2025-09-22_19-44-09/
        ├── iteration_001.png
        ├── iteration_002.png
        ├── final_points.csv
        └── ...

```

## 🛠️ Core Applications

The suite is composed of three interconnected PySide6 applications:

1. **Truss Editor (`editor.py`):**
    
    - **Purpose:** Interactive creation and management of truss data.
        
    - **Functionality:** Allows users to place nodes, connect elements, define boundary conditions (supports), assign loads, and set material properties via an editable table interface. All inputs are handled in the standard CSV format.
        
2. **Truss Optimizer (`optimizer_app.py`):**
    
    - **Purpose:** Running the core structural analysis and numerical optimization.
        
    - **Functionality:** Loads a design, allows the user to set optimization parameters and weights (e.g., objective function definition), and executes the multi-variate optimization algorithms (`optimizer.py`). Outputs the resulting optimized truss configuration.
        
3. **Truss Visualizer (`visualizer.py`):**
    
    - **Purpose:** Dedicated tool for viewing, plotting, and exporting results.
        
    - **Functionality:** Reads truss data (original or optimized) and displays the geometry, loads, supports, calculated displacements, and internal member forces/stresses using Matplotlib. Includes functionality to export high-resolution truss diagrams.
        

## 🏗️ Core Modules

The `src/` directory contains the core Python scripts for the project's logic and user interface components:

- **`truss_model.py`**: Defines the central **TrussModel** class, which encapsulates all structural data (points, trusses, loads, materials, supports) and methods for data integrity and storage.
    
- **`fem_solver.py`**: The **Finite Element Method** (FEM) engine. This script calculates the global stiffness matrix, solves for nodal displacements, and computes internal forces and stresses within the truss.
    
- **`analysis.py`**: Contains the functions necessary for structural **analysis**, including the calculation of performance metrics and the definition of the weighted objective function used to score designs.
    
- **`optimizer.py`**: Implements the **numerical optimization** routines (e.g., gradient-based or iterative algorithms) that systematically adjust design parameters (like node coordinates) to find an optimal solution.
    
- **`ui_components.py`**: Houses custom **GUI components**, such as the PySide6-compatible Matplotlib canvas wrappers (`MplCanvas`), for integrating visualization.
    
- **`ui_themes.py`**: Contains the **Qt Style Sheets** defining the consistent visual appearance of the application (Light and Dark themes).
    

## 📊 Data Schema

All truss designs are defined within subdirectories of the `data/` folder using a set of CSV files.

- **`points.csv`**: Defines the nodes of the truss.
    
    - `Node`: Unique identifier for each node.
        
    - `x`: x-coordinate of the node.
        
    - `y`: y-coordinate of the node.
        
- **`trusses.csv`**: Defines the truss members.
    
    - `element`: Unique identifier for each truss element.
        
    - `start`: The starting node of the truss member.
        
    - `end`: The ending node of the truss member.
        
- **`loads.csv`**: Specifies the external forces applied to the nodes.
    
    - `Node`: The node where the force is applied.
        
    - `Fx`: Force component in the x-direction.
        
    - `Fy`: Force component in the y-direction.
        
- **`materials.csv`**: Contains material properties.
    
    - `E`: Young's Modulus of the material.
        
    - `A`: Cross-sectional area of the truss members.
        
- **`supports.csv`**: Defines the fixed support points.
    
    - `Node`: The node being supported.
        
    - `fix_x`: 1 if x-movement is fixed, 0 otherwise.
        
    - `fix_y`: 1 if y-movement is fixed, 0 otherwise.
        

## 📈 Simulation Output

The `output/` directory stores the results of each simulation run in a timestamped subdirectory.

- **`iteration_XXX.png`**: Screenshots showing the state of the truss at different stages of the optimization (if logging is enabled).
    
- **`final_points.csv`**: The optimized nodal coordinates after the simulation is complete.
    

## 📦 Required Packages

To run this project, you will need the following Python packages:

- `numpy`
    
- `pandas`
    
- `matplotlib`
    
- `scipy`
    
- **`PySide6`** (Required for the GUI application)