# ✨ Numerical Truss Optimizer ✨

A numerical optimizer for truss structures using the Finite Element Method (FEM). This project is designed to analyze and optimize 2D truss designs, providing an intuitive way to experiment with structural mechanics.

-----

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
│   ├── truss_solver.py
│   ├── truss_analysis.py
│   ├── multivariate.py
│   └── multivariate_logging.py
└── output/
    └── 2025-09-22_19-44-09/
        ├── iteration_001.png
        ├── iteration_002.png
        ├── final_points.csv
        └── ...
```

-----

## 📊 Data Schema

All truss designs are defined within subdirectories of the `data/` folder using a set of CSV files.

  * **`points.csv`**: Defines the nodes of the truss.

      * `Node`: Unique identifier for each node.
      * `x`: x-coordinate of the node.
      * `y`: y-coordinate of the node.

  * **`trusses.csv`**: Defines the truss members.

      * `element`: Unique identifier for each truss element.
      * `start`: The starting node of the truss member.
      * `end`: The ending node of the truss member.

  * **`loads.csv`**: Specifies the external forces applied to the nodes.

      * `Node`: The node where the force is applied.
      * `Fx`: Force component in the x-direction.
      * `Fy`: Force component in the y-direction.

  * **`materials.csv`**: Contains material properties.

      * `E`: Young's Modulus of the material.
      * `A`: Cross-sectional area of the truss members.

  * **`supports.csv`**: Defines the fixed support points.

      * `Node`: The node being supported.
      * `fix_x`: 1 if x-movement is fixed, 0 otherwise.
      * `fix_y`: 1 if y-movement is fixed, 0 otherwise.

-----

## 🛠️ Core Modules

The `src/` directory contains the core Python scripts for the project.

  * **`truss_solver.py`**: A **Finite Element Method** (FEM) solver for 2D truss structures. This script takes the data from the CSV files, calculates the nodal displacements, internal forces, and stresses within the truss.
  * **`truss_analysis.py`**: Implements a single-point variation optimizer. It systematically adjusts one parameter at a time to find an optimal design based on a defined objective function.
  * **`multivariate.py`**: Contains a multipoint optimizer for more complex, simultaneous adjustments of multiple design parameters.
  * **`multivariate_logging.py`**: An enhanced version of the multipoint optimizer that logs data and generates visual outputs (`.png` screenshots) for each iteration of the optimization process.

-----

## 📈 Simulation Output

The `output/` directory stores the results of each simulation run in a timestamped subdirectory.

  * **`iteration_XXX.png`**: Screenshots showing the state of the truss at different stages of the optimization.
  * **`final_points.csv`**: The optimized nodal coordinates after the simulation is complete.

-----

## 📦 Required Packages

To run this project, you will need the following Python packages:

  * `numpy`
  * `pandas`
  * `matplotlib`
  * `scipy`
  * `pyqt5`