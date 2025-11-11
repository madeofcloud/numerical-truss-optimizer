# analysis.py

import pandas as pd
import numpy as np

def calculate_buckling_indices(stresses_df):
    """Calculates buckling-related metrics from simulation results."""
    compressive_members = stresses_df[stresses_df['axial_force'] < 0].copy()
    
    if compressive_members.empty or compressive_members['Pc'].isnull().all():
        return {'buckling_distribution_factor': 0.0, 'coefficient_of_variation': 0.0}

    compressive_members.dropna(subset=['Pc'], inplace=True)
    # mu is the ratio of actual axial force to critical buckling force
    compressive_members['mu'] = np.abs(compressive_members['axial_force'] / compressive_members['Pc'])
    
    # Calculate Gamma (Buckling Distribution Factor component)
    numerator = (compressive_members['mu'] * np.abs(compressive_members['axial_force'])).sum()
    denominator = np.abs(compressive_members['axial_force']).sum()
    gamma = numerator / denominator if denominator != 0 else 0
    
    # Calculate Sigma_mu (Standard Deviation component)
    weights = np.abs(compressive_members['axial_force'])
    variance = np.average((compressive_members['mu'] - gamma)**2, weights=weights)
    s_mu = np.sqrt(variance)

    # Buckling Distribution Factor (Gamma + 2 * Sigma_mu)
    buckling_distribution_factor = gamma + 2 * s_mu
    
    # Coefficient of Variation (s_mu / Gamma) for uniformity
    v_mu = s_mu / gamma if gamma != 0 else float('inf')
    
    return {
        'buckling_distribution_factor': buckling_distribution_factor,
        'coefficient_of_variation': v_mu
    }

def calculate_buckling_penalty(stresses_df, threshold=0.9):
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
    # """Applies a high penalty if any member exceeds a buckling utilization threshold."""
    #     compressive_members = stresses_df[stresses_df['axial_force'] < 0]
    #     if compressive_members.empty or compressive_members['Pc'].isnull().all():
    #         return 0.0

    #     compressive_members.dropna()
    #     utilization = np.abs(compressive_members['axial_force'] / compressive_members['Pc'])
        
    #     # Check if any member utilization exceeds the threshold
    #     if (utilization > threshold).any():
    #         # Penalty is the maximum utilization ratio above threshold, squared for aggressive minimization
    #         max_utilization = utilization.max()
    #         if max_utilization > 1.0:
    #             return 10.0 * (max_utilization - 1.0)**2 # Severe penalty for failure (utilization > 1)
    #         else:
    #             return 1.0 * (max_utilization - threshold) # Smaller penalty for near-failure
        
    #     return 0.0

def normalized_material_usage(stresses_df, initial_lengths):
    """Calculates the ratio of current material usage (Volume) to initial usage."""
    # Volume = sum(Length * Area)
    current_volume = (stresses_df['L'] * stresses_df['A']).sum()
    initial_volume = (initial_lengths * stresses_df['A'].head(len(initial_lengths))).sum()
    
    return current_volume / initial_volume if initial_volume > 0 else 1.0

def normalized_average_force(stresses_df, initial_forces):
    """Calculates the ratio of current average absolute force to initial average force."""
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
    
    if stresses_df.empty:
        # Return a very high score if analysis failed
        return 1e9, {'Total Score': 1e9, 'Buckling Distribution Factor': 0.0, 'Compression Uniformity': 0.0, 'Material Usage Ratio': 1.0, 'Buckling Penalty': 1.0}
    
    # Calculate all individual metric scores
    buckling_metrics = calculate_buckling_indices(stresses_df)
    buckling_penalty = calculate_buckling_penalty(stresses_df)
    material_usage = normalized_material_usage(stresses_df, model.initial_lengths)
    avg_force = normalized_average_force(stresses_df, model.initial_forces)
    
    # Combine scores using weights
    unnormalized_score = (
        buckling_metrics['buckling_distribution_factor'] * weights['buckling_distribution_factor'] +
        buckling_penalty * weights['buckling_penalty'] +
        material_usage * weights['material_usage'] +
        buckling_metrics['coefficient_of_variation'] * weights['compressive_uniformity'] +
        avg_force * weights['average_force_magnitude']
    )

    total_weight = sum(weights.values())
    score = unnormalized_score / total_weight if total_weight > 0 else float('inf')
    
    # Bundle metrics for display
    metrics = {
        'Total Score': score,
        'Buckling Distribution Factor': buckling_metrics['buckling_distribution_factor'],
        'Compression Uniformity': buckling_metrics['coefficient_of_variation'],
        'Material Usage Ratio': material_usage,
        'Buckling Penalty': buckling_penalty,
        'Average Force Ratio': avg_force
    }
    
    return score, metrics
