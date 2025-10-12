# Truss Suite: Numerical Truss Optimizer & Editor

**Truss Suite** is an integrated application for the analysis, design, and optimization of 2D and 3D truss structures using the Finite Element Method (FEM), created for the **4CBLA00** course at TU/e.

It provides an intuitive graphical interface for structural modeling, optimization, and visualization, built using **PySide6**, **NumPy**, **SciPy**, **Pandas**, and **Matplotlib**.

The suite is managed through a single **Launcher** that gives access to the following tools:

- **Editor**
- **Optimizer (2D)**
- **Optimizer 3D**
- **Visualizer**

---
## Easy Usage

The Truss Suite can be launched either from a pre-built executable or directly from the source code.

### 1. From a Release Build (.exe)

1. **Download:** Obtain the latest compiled executable (e.g. `TrussSuite.exe`) from the project’s [Releases page](https://github.com/madeofcloud/numerical-truss-optimizer/releases).
2. **Run:** Double-click `TrussSuite.exe` to launch the application.

### 2. From Source (Python)

1. **Install Requirements:**  
    Ensure all required packages listed under [Required Packages](#required-packages) are installed.
2. **Launch the Application:**  
    From the `src/` directory, run:
    `python launcher.py`

---
## Workflow Steps

1. **Edit:** Use the **Editor** to define truss geometry, supports, loads, and materials. All data is stored as CSV files in the `data/` directory.
    
2. **Optimize:** Run the **Optimizer (2D)** or **Optimizer 3D** to define objectives (e.g. stiffness, weight) and perform numerical optimization.
    
3. **Visualize:** Open results in the **Visualizer** to inspect deformed shapes, forces, and export high-quality diagrams.
    

Data formats are detailed in the [Data Schema](#data-schema).

---

## Project Structure

```
.
├── data/
│   ├── design_1/
│   │   ├── loads.csv
│   │   ├── materials.csv
│   │   ├── points.csv
│   │   ├── supports.csv
│   │   └── trusses.csv
│   └── ...
├── src/
│   ├── launcher.py
│   ├── editor/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── visualizer/
│   │   ├── __init__.py
│   │   └── main.py
│   ├── optimizer/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── fem_solver.py
│   │   ├── optimizer.py
│   │   ├── truss_model.py
│   │   ├── analysis.py
│   │   ├── ui_components.py
│   │   └── ui_themes.py
│   └── optimizer_3d/
│       ├── __init__.py
│       ├── main.py
│       ├── fem_solver.py
│       ├── optimizer.py
│       ├── truss_model.py
│       ├── analysis.py
│       ├── ui_components.py
│       └── ui_themes.py
├── output/
│   └── 2025-09-22_19-44-09/
│       ├── iteration_001.png
│       ├── iteration_002.png
│       ├── final_points.csv
│       └── ...
└── venv/ # Create a Python venv for development
	└── ...

```

---

## Core Applications

### 1. Editor (`editor/main.py`)

- **Purpose:** Define and modify truss geometry, materials, loads, and supports.
    
- **Features:** Interactive node and element placement, editable tables, CSV import/export.

### 2. Optimizer (`optimizer/main.py`)

- **Purpose:** Perform numerical optimization on 2D truss structures.
    
- **Modules:**
    
    - `fem_solver.py` – FEM engine for stiffness and displacement computation.
        
    - `optimizer.py` – Optimization algorithms.
        
    - `truss_model.py` – Data model for truss state.
        
    - `analysis.py` – Objective and fitness functions.
        
    - `ui_components.py`, `ui_themes.py` – GUI elements and visual themes.

### 3. Optimizer 3D (`optimizer_3d/main.py`)

- **Purpose:** Extension of the optimizer for 3D truss systems.
    
- **Structure:** Identical to the 2D optimizer, but supports three spatial dimensions and 3D visualization.

### 4. Visualizer (`visualizer/main.py`)

- **Purpose:** Visual inspection and export of analysis and optimization results.
    
- **Features:** Displays loads, supports, internal forces, and deformed configurations using Matplotlib.

---

## Data Schema

All truss models are defined within subdirectories of `data/`, using CSV files for each data type.

### `points.csv`

Defines node coordinates.  
Supports both 2D (x, y) and 3D (x, y, z) data.

|Node|x|y|z (optional)|
|---|---|---|---|
|number|number|number|number|

### `trusses.csv`

Defines structural elements and their material assignments.

|element|start|end|material_id|
|---|---|---|---|
|number|number|number|number|

### `loads.csv`

Specifies external nodal forces.  
In 2D, only `Fx`, `Fy` are used; in 3D, `Fz` is added.

|Node|Fx|Fy|Fz (optional)|
|---|---|---|---|
|number|number|number|number|

### `materials.csv`

Defines material and section properties.

|material_id|E|A|I|
|---|---|---|---|
|Unique ID|Young’s Modulus|Cross-sectional area|Second moment of area|

### `supports.csv`

Specifies fixed degrees of freedom.  
In 2D, only `Rx`, `Ry` are used; in 3D, add `Rz`.

| Node | Rx  | Ry  | Rz (optional) |
| ---- | --- | --- | ------------- |
|number|0=False; 1=True|0=False; 1=True|0=False; 1=True|

---

## Simulation Output

Each run generates a timestamped directory in `output/` containing:

- `final_points.csv`: Final optimized nodal coordinates

---

## Required Packages

Install the following dependencies:

- `numpy`
- `pandas`
- `matplotlib`
- `scipy`
- `PySide6`