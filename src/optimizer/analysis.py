# analysis.py

import pandas as pd
import numpy as np

def calculate_buckling_indices(stresses_df):
    """Calculates buckling-related metrics from simulation results."""
    compressive_members = stresses_df[stresses_df['axial_force'] < 0].copy()
    
    if compressive_members.empty or compressive_members['Pc'].isnull().all():
        return {'buckling_distribution_factor': 0.0, 'coefficient_of_variation': 0.0}

    compressive_members.dropna(subset=['Pc'], inplace=True)
    compressive_members['mu'] = np.abs(compressive_members['axial_force'] / compressive_members['Pc'])
    
    numerator = (compressive_members['mu'] * np.abs(compressive_members['axial_force'])).sum()
    denominator = np.abs(compressive_members['axial_force']).sum()
    gamma = numerator / denominator if denominator != 0 else 0
    
    weights = np.abs(compressive_members['axial_force'])
    variance = np.average((compressive_members['mu'] - gamma)**2, weights=weights)
    s_mu = np.sqrt(variance)

    buckling_distribution_factor = gamma + 2 * s_mu
    v_mu = s_mu / gamma if gamma != 0 else float('inf')
    
    return {
        'buckling_distribution_factor': buckling_distribution_factor,
        'coefficient_of_variation': v_mu
    }

def calculate_buckling_penalty(stresses_df):
    """Calculates a penalty if any member's buckling utilization exceeds 1."""
    if stresses_df.empty:
        return 1e6 # High penalty if solver fails
    
    compressive_members = stresses_df[stresses_df['axial_force'] < 0].copy()
    if not compressive_members.empty:
        compressive_members.dropna(subset=['Pc'], inplace=True)
        mu = np.abs(compressive_members['axial_force'] / compressive_members['Pc'])
        if np.any(mu >= 1):
            return 100.0
    return 0.0

def normalized_material_usage(stresses_df, initial_lengths):
    """Calculates normalized material usage."""
    if stresses_df.empty or 'A' not in stresses_df.columns or 'L' not in stresses_df.columns:
        return 1e6
    
    current_usage = (stresses_df['A'] * stresses_df['L']).sum()
    initial_usage = (stresses_df['A'] * initial_lengths).sum()
    return current_usage / initial_usage if initial_usage > 0 else 0

def normalized_average_force(stresses_df, initial_forces):
    """Calculates the normalized average magnitude of internal forces."""
    if stresses_df.empty or initial_forces.empty:
        return 1e6
    
    avg_force = np.mean(np.abs(stresses_df['axial_force']))
    initial_avg_force = np.mean(np.abs(initial_forces))
    return avg_force / initial_avg_force if initial_avg_force > 0 else 0

def get_objective(model, weights):
    """
    Combines all metrics from a TrussModel into a single objective score.
    """
    if not model.is_analyzed:
        model.run_analysis()
    
    stresses_df = model.stresses_df
    
    # Calculate all individual metric scores
    buckling_metrics = calculate_buckling_indices(stresses_df)
    buckling_penalty = calculate_buckling_penalty(stresses_df)
    material_usage = normalized_material_usage(stresses_df, model.initial_lengths)
    avg_force = normalized_average_force(stresses_df, model.initial_forces)
    
    # Combine scores using weights
    score = (
        buckling_metrics['buckling_distribution_factor'] * weights['buckling_distribution_factor'] +
        buckling_penalty * weights['buckling_penalty'] +
        material_usage * weights['material_usage'] +
        buckling_metrics['coefficient_of_variation'] * weights['compressive_uniformity'] +
        avg_force * weights['average_force_magnitude']
    )
    
    # Bundle metrics for display
    metrics = {
        'Total Score': score,
        'Buckling Distribution Factor': buckling_metrics['buckling_distribution_factor'],
        'Compression Uniformity': buckling_metrics['coefficient_of_variation'],
        'Buckling Penalty': buckling_penalty,
        'Material Usage': material_usage,
        'Average Force Magnitude': avg_force
    }
    
    return score, metrics