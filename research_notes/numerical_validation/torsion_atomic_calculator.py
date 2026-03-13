#!/usr/bin/env python3
"""
Torsion-Corrected Atomic Structure Calculator
==============================================

Computes atomic energy levels with torsion corrections at high precision.

Author: Unified Field Theory Research Team
Date: 2026-03-14
Version: 1.0
"""

import numpy as np
from scipy import linalg, integrate, optimize
from scipy.special import factorial, eval_genlaguerre, sph_harm_y
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Tuple, List, Dict
import json

# Physical constants
ALPHA = 1/137.035999084  # Fine structure constant
M_ELECTRON = 511e3  # eV
HARTREE = 27.211386245988  # eV
BOHR_RADIUS = 0.529177210903e-10  # m
HBARC = 197.3269804  # MeV·fm


@dataclass
class TorsionParameters:
    """Torsion field parameters"""
    tau_0: float = 1e-6  # Base torsion parameter
    alpha_run: float = 1e-3  # Running parameter
    coupling_g: float = 1.0  # Coupling constant
    form_factor_n: float = 2.0  # Form factor exponent
    
    def effective_tau(self, energy_scale: float, e_gut: float = 1e16) -> float:
        """
        Calculate scale-dependent effective torsion
        
        Args:
            energy_scale: Energy scale in eV
            e_gut: GUT scale in eV
            
        Returns:
            Effective torsion at given scale
        """
        x = energy_scale / e_gut
        form_factor = x**self.form_factor_n / (1 + x**self.form_factor_n)
        return self.tau_0 * form_factor


@dataclass
class AtomicState:
    """Atomic state quantum numbers"""
    n: int  # Principal quantum number
    l: int  # Orbital angular momentum
    j: float  # Total angular momentum
    m_j: float  # Magnetic quantum number
    
    def __post_init__(self):
        assert abs(self.m_j) <= self.j
        assert self.l >= 0
        assert self.n > self.l


class TorsionDiracSolver:
    """
    Solver for torsion-corrected Dirac equation for hydrogen-like atoms
    """
    
    def __init__(self, Z: int, torsion_params: TorsionParameters):
        """
        Initialize solver
        
        Args:
            Z: Nuclear charge
            torsion_params: Torsion field parameters
        """
        self.Z = Z
        self.tau_params = torsion_params
        self.energy_scale = Z**2 * ALPHA**2 * M_ELECTRON / 2  # Characteristic energy
        self.tau_eff = torsion_params.effective_tau(self.energy_scale)
        
    def dirac_energy_exact(self, n: int, kappa: int) -> float:
        """
        Exact Dirac energy for hydrogen-like atom
        
        Args:
            n: Principal quantum number
            kappa: Dirac quantum number κ = -(j + 1/2) for j = l + 1/2
                                          = +(j + 1/2) for j = l - 1/2
                                          
        Returns:
            Energy in eV (negative for bound states)
        """
        gamma = np.sqrt(kappa**2 - (self.Z * ALPHA)**2)
        denominator = np.sqrt(n**2 - 2*(n - abs(kappa))*(abs(kappa) - gamma))
        energy = M_ELECTRON * (1 + (self.Z * ALPHA / denominator)**2)**(-0.5)
        return energy - M_ELECTRON  # Binding energy
    
    def torsion_mass_correction(self, n: int, l: int) -> float:
        """
        Calculate torsion-induced mass correction
        
        ΔE_mass = -(1/3) τ² E_n
        
        Args:
            n: Principal quantum number
            l: Orbital angular momentum
            
        Returns:
            Energy correction in eV
        """
        E_n = -self.Z**2 * HARTREE / (2 * n**2)
        return -(1/3) * self.tau_eff**2 * E_n
    
    def torsion_spin_coupling(self, state: AtomicState) -> float:
        """
        Calculate spin-torsion coupling energy
        
        H_τ-spin = g_τ τ (ℏ/2m)² L·S ∇²
        
        Args:
            state: Atomic state
            
        Returns:
            Energy correction in eV
        """
        n, l, j = state.n, state.l, state.j
        
        # Calculate <L·S>
        s = 0.5
        L_dot_S = 0.5 * (j*(j+1) - l*(l+1) - s*(s+1))
        
        # For hydrogen-like atoms, <∇²> = -5/(4a₀²) for 2P states
        # General formula: <∇²> = -Z²/(a₀²n²) × [3 - l(l+1)/n²]
        a_0_eff = BOHR_RADIUS / self.Z
        if n == 2 and l == 1:
            exp_laplacian = -5 / (4 * a_0_eff**2)
        else:
            exp_laplacian = -self.Z**2 / (a_0_eff**2 * n**2) * (3 - l*(l+1)/n**2)
        
        # Energy scale factor
        prefactor = self.tau_params.coupling_g * self.tau_eff * (HBARC * 1e-15)**2
        prefactor *= (self.Z * ALPHA)**4 * M_ELECTRON / 2
        
        return prefactor * L_dot_S * exp_laplacian * (BOHR_RADIUS**2)
    
    def torsion_orbital_correction(self, n: int, l: int) -> float:
        """
        Calculate orbital torsion correction
        
        H_τ-orb = (ℏ²/8m) τ² ∇²
        
        Args:
            n: Principal quantum number
            l: Orbital angular momentum
            
        Returns:
            Energy correction in eV
        """
        a_0_eff = BOHR_RADIUS / self.Z
        if n == 2 and l == 1:
            exp_laplacian = -5 / (4 * a_0_eff**2)
        else:
            exp_laplacian = -self.Z**2 / (a_0_eff**2 * n**2) * (3 - l*(l+1)/n**2)
        
        prefactor = self.tau_eff**2 * (HBARC * 1e-15)**2 / (8 * M_ELECTRON * 1e-6)
        return prefactor * exp_laplacian
    
    def calculate_fine_structure(self, n: int, l: int) -> Tuple[float, float]:
        """
        Calculate fine structure splitting
        
        Args:
            n: Principal quantum number
            l: Orbital angular momentum
            
        Returns:
            (E_j=l-1/2, E_j=l+1/2) tuple in eV
        """
        if l == 0:
            # S-states don't have fine structure splitting
            E_n = -self.Z**2 * HARTREE / (2 * n**2)
            return (E_n, E_n)
        
        # Fine structure formula
        E_n = -self.Z**2 * HARTREE / (2 * n**2)
        alpha_Z = self.Z * ALPHA
        
        # j = l ± 1/2
        j_plus = l + 0.5
        j_minus = l - 0.5
        
        # Fine structure correction: ΔE_FS = E_n²/(2mₑc²) × [4n/(j+1/2) - 3]
        delta_E_plus = (E_n**2 / (2 * M_ELECTRON)) * (4*n/(j_plus + 0.5) - 3)
        delta_E_minus = (E_n**2 / (2 * M_ELECTRON)) * (4*n/(j_minus + 0.5) - 3)
        
        return (E_n + delta_E_minus, E_n + delta_E_plus)
    
    def calculate_energy_with_torsion(self, state: AtomicState) -> Dict[str, float]:
        """
        Calculate total energy with all torsion corrections
        
        Args:
            state: Atomic state
            
        Returns:
            Dictionary of energy components and total
        """
        n, l, j = state.n, state.l, state.j
        
        # Base energy (Dirac)
        kappa = int(-(j + 0.5)) if j == l + 0.5 else int(j + 0.5)
        E_dirac = self.dirac_energy_exact(n, kappa)
        
        # Fine structure (already included in Dirac, but calculate separately for comparison)
        E_fs_low, E_fs_high = self.calculate_fine_structure(n, l)
        E_fs = E_fs_high if j == l + 0.5 else E_fs_low
        
        # Torsion corrections
        delta_E_mass = self.torsion_mass_correction(n, l)
        delta_E_spin = self.torsion_spin_coupling(state)
        delta_E_orb = self.torsion_orbital_correction(n, l)
        
        total_torsion = delta_E_mass + delta_E_spin + delta_E_orb
        
        return {
            'E_dirac': E_dirac,
            'E_fine_structure': E_fs,
            'delta_E_mass': delta_E_mass,
            'delta_E_spin': delta_E_spin,
            'delta_E_orbital': delta_E_orb,
            'delta_E_total_torsion': total_torsion,
            'E_total': E_dirac + total_torsion,
            'tau_eff': self.tau_eff
        }


class ManyElectronAtom:
    """
    Torsion-corrected calculations for many-electron atoms
    Using Dirac-Fock approach
    """
    
    def __init__(self, Z: int, torsion_params: TorsionParameters):
        self.Z = Z
        self.tau_params = torsion_params
        self.energy_scale = Z**2 * ALPHA**2 * M_ELECTRON / 2
        self.tau_eff = torsion_params.effective_tau(self.energy_scale)
        
    def slater_screening(self, n: int, l: int, electron_config: List[Tuple[int, int, int]]) -> float:
        """
        Calculate Slater screening constant
        
        Args:
            n, l: Quantum numbers of electron
            electron_config: List of (n, l, count) for each subshell
            
        Returns:
            Screening constant σ
        """
        sigma = 0.0
        for n_i, l_i, count in electron_config:
            if n_i < n:
                sigma += count
            elif n_i == n:
                if l_i < l:
                    sigma += count
                elif l_i == l:
                    sigma += 0.35 * (count - 1)  # Same group
                else:
                    sigma += 0.0  # Higher l shields less
            else:
                sigma += 0.0
        
        # 1s electrons shield differently
        if n > 1:
            sigma += 0.30  # Each 1s electron contributes 0.30
            
        return sigma
    
    def effective_nuclear_charge(self, n: int, l: int, electron_config: List[Tuple[int, int, int]]) -> float:
        """Calculate effective nuclear charge Z_eff = Z - σ"""
        sigma = self.slater_screening(n, l, electron_config)
        return self.Z - sigma
    
    def torsion_screening_correction(self, n: int, l: int) -> float:
        """
        Torsion correction to screening constant
        
        Δσ_τ = α_τ τ² sin(2πZ/8)
        
        This creates periodic modulation of properties
        """
        alpha_tau = 0.01  # Empirical parameter
        return alpha_tau * self.tau_eff**2 * np.sin(2 * np.pi * self.Z / 8)


def calculate_hydrogen_spectrum(tau_0: float = 1e-6) -> Dict:
    """
    Calculate complete hydrogen spectrum with torsion corrections
    
    Args:
        tau_0: Base torsion parameter
        
    Returns:
        Dictionary with energy levels and splittings
    """
    params = TorsionParameters(tau_0=tau_0)
    solver = TorsionDiracSolver(Z=1, torsion_params=params)
    
    results = {
        'tau_0': tau_0,
        'tau_eff': solver.tau_eff,
        'levels': []
    }
    
    # Calculate 1S, 2S, 2P levels
    states = [
        AtomicState(1, 0, 0.5, 0.5),
        AtomicState(2, 0, 0.5, 0.5),
        AtomicState(2, 1, 0.5, 0.5),  # 2P_1/2
        AtomicState(2, 1, 1.5, 1.5),  # 2P_3/2
    ]
    
    for state in states:
        energies = solver.calculate_energy_with_torsion(state)
        results['levels'].append({
            'n': state.n,
            'l': state.l,
            'j': state.j,
            **energies
        })
    
    # Calculate Lamb shift (2S_1/2 - 2P_1/2)
    E_2S = results['levels'][1]['E_total']
    E_2P_12 = results['levels'][2]['E_total']
    lamb_shift = E_2S - E_2P_12
    
    # Calculate fine structure (2P_3/2 - 2P_1/2)
    E_2P_32 = results['levels'][3]['E_total']
    fine_structure = E_2P_32 - E_2P_12
    
    results['lamb_shift'] = lamb_shift
    results['fine_structure'] = fine_structure
    results['torsion_contribution_to_fs'] = (
        results['levels'][3]['delta_E_total_torsion'] - 
        results['levels'][2]['delta_E_total_torsion']
    )
    
    return results


def calculate_highly_charged_ion(Z: int, tau_0: float = 1e-6) -> Dict:
    """
    Calculate energy levels for hydrogen-like ion with nuclear charge Z
    
    The torsion effects scale as Z⁴, making them more detectable in HCI
    
    Args:
        Z: Nuclear charge
        tau_0: Base torsion parameter
        
    Returns:
        Dictionary with energy levels
    """
    params = TorsionParameters(tau_0=tau_0)
    solver = TorsionDiracSolver(Z=Z, torsion_params=params)
    
    # 2P state fine structure
    state_2P_12 = AtomicState(2, 1, 0.5, 0.5)
    state_2P_32 = AtomicState(2, 1, 1.5, 1.5)
    
    E_12 = solver.calculate_energy_with_torsion(state_2P_12)
    E_32 = solver.calculate_energy_with_torsion(state_2P_32)
    
    fine_structure = E_32['E_total'] - E_12['E_total']
    torsion_contribution = E_32['delta_E_total_torsion'] - E_12['delta_E_total_torsion']
    
    return {
        'Z': Z,
        'ion': f'{Z}+',
        'tau_eff': solver.tau_eff,
        'fine_structure_eV': fine_structure,
        'fine_structure_GHz': fine_structure / (4.135667696e-6),  # Convert to GHz
        'torsion_contribution_eV': torsion_contribution,
        'torsion_contribution_MHz': torsion_contribution / (4.135667696e-9),
        'relative_torsion_effect': abs(torsion_contribution / fine_structure)
    }


def generate_comparison_table():
    """Generate comparison table for various atoms and ions"""
    print("=" * 80)
    print("TORSION-CORRECTED ATOMIC ENERGY LEVELS")
    print("=" * 80)
    
    # Hydrogen
    print("\n1. HYDROGEN ATOM (Z=1)")
    print("-" * 40)
    h_results = calculate_hydrogen_spectrum(tau_0=1e-6)
    print(f"τ₀ = {h_results['tau_0']:.0e}")
    print(f"τ_eff = {h_results['tau_eff']:.2e}")
    print(f"\nLamb shift (2S_1/2 - 2P_1/2): {h_results['lamb_shift']*1e6:.4f} μeV")
    print(f"Fine structure (2P): {h_results['fine_structure']*1e6:.2f} μeV = {h_results['fine_structure']/4.135667696e-9:.2f} GHz")
    print(f"Torsion contribution to FS: {h_results['torsion_contribution_to_fs']*1e9:.4f} neV = {h_results['torsion_contribution_to_fs']/4.135667696e-12:.2f} mHz")
    
    # Highly charged ions
    print("\n2. HIGHLY CHARGED IONS (2P Fine Structure)")
    print("-" * 40)
    print(f"{'Ion':<10} {'τ_eff':<12} {'FS [GHz]':<15} {'τ contrib [MHz]':<18} {'Rel. Effect'}")
    print("-" * 70)
    
    for Z in [26, 54, 82, 92]:  # Fe, Xe, Pb, U
        result = calculate_highly_charged_ion(Z, tau_0=1e-6)
        print(f"{result['ion']:<10} {result['tau_eff']:<12.2e} {result['fine_structure_GHz']:<15.2f} "
              f"{result['torsion_contribution_MHz']:<18.4f} {result['relative_torsion_effect']:.2e}")
    
    # Parameter scan
    print("\n3. PARAMETER SCAN: Hydrogen Fine Structure vs τ₀")
    print("-" * 40)
    print(f"{'τ₀':<12} {'τ_eff':<12} {'Torsion [MHz]':<15} {'Exp. Limit [MHz]'}")
    print("-" * 55)
    
    for tau_0 in [1e-8, 1e-7, 1e-6, 1e-5, 1e-4]:
        result = calculate_hydrogen_spectrum(tau_0=tau_0)
        torsion_mhz = result['torsion_contribution_to_fs'] / 4.135667696e-9
        print(f"{tau_0:<12.0e} {result['tau_eff']:<12.2e} {torsion_mhz:<15.6f} {'< 1.0':<15}")
    
    print("\n" + "=" * 80)


def save_results_json(filename: str = "atomic_calculations_results.json"):
    """Save all calculation results to JSON file"""
    results = {
        'metadata': {
            'date': '2026-03-14',
            'version': '1.0',
            'theory': 'Unified Field Theory with Torsion'
        },
        'hydrogen': calculate_hydrogen_spectrum(tau_0=1e-6),
        'highly_charged_ions': {}
    }
    
    for Z in [26, 54, 79, 82, 92]:
        results['highly_charged_ions'][f'Z{Z}'] = calculate_highly_charged_ion(Z, tau_0=1e-6)
    
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Results saved to {filename}")


if __name__ == "__main__":
    # Generate comparison table
    generate_comparison_table()
    
    # Save results to JSON
    save_results_json()
    
    print("\n✅ Atomic structure calculations complete!")
