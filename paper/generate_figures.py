#!/usr/bin/env python3
"""
Generate figures for UFT paper
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch
import matplotlib.patches as mpatches

# Set style
plt.style.use('seaborn-v0_8-paper')
plt.rcParams['font.size'] = 10
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['legend.fontsize'] = 9

def fig_spectral_dimension():
    """Figure 1: Spectral dimension evolution"""
    fig, ax = plt.subplots(figsize=(6, 4))
    
    E = np.logspace(16, 19, 500)  # Energy in GeV
    E_c = 1e16  # GUT scale
    d_s = 4 + 6 / (1 + (E_c/E)**2)
    
    ax.semilogx(E, d_s, 'b-', linewidth=2, label=r'$d_s(E)$')
    ax.axhline(y=4, color='r', linestyle='--', alpha=0.7, label='Low energy: $d_s = 4$')
    ax.axhline(y=10, color='g', linestyle='--', alpha=0.7, label='Planck: $d_s = 10$')
    ax.axvline(x=E_c, color='purple', linestyle=':', alpha=0.7, label=r'$E_{GUT} = 10^{16}$ GeV')
    
    # Annotations
    ax.annotate('Classical\\nspacetime', xy=(1e12, 4.5), fontsize=9, ha='center')
    ax.annotate('String/Quantum\\nGravity regime', xy=(5e18, 9), fontsize=9, ha='center')
    
    ax.set_xlabel('Energy $E$ [GeV]')
    ax.set_ylabel('Spectral Dimension $d_s$')
    ax.set_title('Dynamic Spectral Dimension Evolution')
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))
    ax.grid(True, alpha=0.3)
    ax.set_xlim([1e12, 1e20])
    ax.set_ylim([3, 11])
    
    plt.tight_layout()
    plt.savefig('/root/.openclaw/workspace/paper/figures/fig1_spectral_dimension.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Figure 1: Spectral dimension evolution")

def fig_polarizations():
    """Figure 2: Six gravitational wave polarizations"""
    fig, axes = plt.subplots(2, 3, figsize=(10, 6))
    axes = axes.flatten()
    
    # Common parameters
    x = np.linspace(0, 4*np.pi, 100)
    k = 1  # wave number
    
    polarizations = [
        ('Plus $h_+$', lambda x: np.cos(k*x)),
        ('Cross $h_\\times$', lambda x: np.sin(k*x)),
        ('Vector-x $h_x$', lambda x: 0.5e-6*np.cos(k*x)),
        ('Vector-y $h_y$', lambda x: 0.5e-6*np.sin(k*x)),
        ('Breathing $h_b$', lambda x: 0.3e-12*np.cos(k*x)),
        ('Longitudinal $h_l$', lambda x: 0.2e-12*np.cos(k*x)),
    ]
    
    for i, (title, func) in enumerate(polarizations):
        y = func(x)
        axes[i].plot(x, y, 'b-', linewidth=2)
        axes[i].fill_between(x, 0, y, alpha=0.3)
        axes[i].set_title(title, fontsize=11)
        axes[i].set_xlabel('Position $x$')
        axes[i].set_ylabel('Strain $h$')
        axes[i].grid(True, alpha=0.3)
        axes[i].axhline(y=0, color='k', linestyle='-', linewidth=0.5)
    
    plt.suptitle('Six Gravitational Wave Polarization Modes ($\\tau_0 = 10^{-6}$)', fontsize=13, y=1.02)
    plt.tight_layout()
    plt.savefig('/root/.openclaw/workspace/paper/figures/fig2_polarizations.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Figure 2: Six GW polarizations")

def fig_lisa_sensitivity():
    """Figure 3: LISA sensitivity and UFT predictions"""
    fig, ax = plt.subplots(figsize=(7, 5))
    
    # LISA sensitivity curve (simplified)
    f = np.logspace(-4, 0, 100)
    h_c_lisa = 1e-21 * (f/1e-3)**(-2) * np.sqrt(1 + (f/1e-3)**4)
    
    # Standard GR signal (2 polarizations)
    f_signal = np.logspace(-4, -1, 50)
    h_c_gr = 1e-20 * (f_signal/1e-3)**(-2/3)
    
    # UFT signal (6 polarizations)
    h_c_uft = h_c_gr * np.sqrt(1 + 2*(0.5e-6)**2)  # Slight enhancement
    
    ax.loglog(f, h_c_lisa, 'k--', linewidth=2, label='LISA Sensitivity')
    ax.loglog(f_signal, h_c_gr, 'b-', linewidth=2, label='Standard GR (2 polarizations)')
    ax.loglog(f_signal, h_c_uft, 'r-', linewidth=2, label='UFT (6 polarizations)')
    
    # SNR annotation
    ax.annotate('SNR ~ 7\\n($\\tau_0 = 10^{-6}$)', 
                xy=(1e-2, 3e-21), fontsize=10,
                bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))
    
    ax.set_xlabel('Frequency $f$ [Hz]')
    ax.set_ylabel('Characteristic Strain $h_c$')
    ax.set_title('LISA Sensitivity and UFT Predictions')
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.set_xlim([1e-4, 1])
    ax.set_ylim([1e-24, 1e-18])
    
    plt.tight_layout()
    plt.savefig('/root/.openclaw/workspace/paper/figures/fig3_lisa_sensitivity.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Figure 3: LISA sensitivity")

def fig_black_hole_structure():
    """Figure 4: Black hole fractal-twisting structure"""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Draw black hole structure
    # Event horizon
    horizon = Circle((0, 0), 3, fill=False, edgecolor='black', linewidth=3, label='Event Horizon')
    ax.add_patch(horizon)
    
    # Fractal core
    for i, r in enumerate(np.linspace(0.1, 2.5, 10)):
        alpha = 1 - i/10
        circle = Circle((0, 0), r, fill=True, facecolor='blue', alpha=alpha*0.1, edgecolor='none')
        ax.add_patch(circle)
    
    # Labels
    ax.annotate('Torsion-Saturated\\nFractal Core', xy=(0, 0), fontsize=11, ha='center', va='center', fontweight='bold')
    ax.annotate('Event Horizon\\n($r = r_s$)', xy=(3.5, 0), fontsize=10, ha='left', va='center')
    ax.annotate('Fractal Zone\\n($d_s < 4$)', xy=(1.5, 2.2), fontsize=10, ha='center')
    
    # Torsion arrows
    for angle in np.linspace(0, 2*np.pi, 8, endpoint=False):
        x_start = 0.5 * np.cos(angle)
        y_start = 0.5 * np.sin(angle)
        x_end = 2.0 * np.cos(angle)
        y_end = 2.0 * np.sin(angle)
        ax.annotate('', xy=(x_end, y_end), xytext=(x_start, y_start),
                   arrowprops=dict(arrowstyle='->', color='red', lw=1.5))
    
    ax.set_xlim([-5, 5])
    ax.set_ylim([-4, 4])
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Fractal-Twisting Black Hole Structure', fontsize=13)
    
    # Legend
    legend_elements = [
        mpatches.Patch(color='blue', alpha=0.3, label='Fractal Core'),
        plt.Line2D([0], [0], color='red', lw=2, label='Torsion Field')
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    plt.savefig('/root/.openclaw/workspace/paper/figures/fig4_black_hole.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Figure 4: Black hole structure")

def fig_cosmology_timeline():
    """Figure 5: Cosmological timeline with spectral dimension"""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
    
    # Time axis (log scale)
    t = np.logspace(-44, 17, 500)  # seconds
    t_planck = 5.39e-44
    t_gut = 1e-36
    t_inflation_end = 1e-32
    t_bbn = 1
    t_now = 4.3e17
    
    # Spectral dimension evolution
    T = 1/np.sqrt(t + 1e-50) * 1e10  # Simplified temperature relation
    d_s = 4 + 6 / (1 + (T/1e16)**2)
    d_s = np.clip(d_s, 4, 10)
    
    ax1.semilogx(t, d_s, 'b-', linewidth=2)
    ax1.fill_between(t, 4, d_s, alpha=0.3)
    ax1.axhline(y=4, color='r', linestyle='--', alpha=0.7)
    ax1.axhline(y=10, color='g', linestyle='--', alpha=0.7)
    
    # Epoch labels
    epochs = [
        (1e-40, 9.5, 'Planck\\n$d_s=10$'),
        (1e-34, 8, 'GUT\\n$d_s=7$'),
        (1e-30, 5.5, 'Inflation\\n$d_s=5$'),
        (1e-10, 4.5, 'Standard\\n$d_s=4$'),
        (1e15, 4.5, 'Today'),
    ]
    for t_pos, d_pos, label in epochs:
        ax1.annotate(label, xy=(t_pos, d_pos), fontsize=9, ha='center')
    
    ax1.set_ylabel('Spectral Dimension $d_s$')
    ax1.set_title('Cosmological Evolution of Spectral Dimension')
    ax1.set_ylim([3.5, 10.5])
    ax1.grid(True, alpha=0.3)
    
    # Temperature
    ax2.loglog(t, T, 'r-', linewidth=2)
    ax2.set_xlabel('Cosmic Time $t$ [s]')
    ax2.set_ylabel('Temperature $T$ [GeV]')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('/root/.openclaw/workspace/paper/figures/fig5_cosmology_timeline.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("✓ Figure 5: Cosmology timeline")

def main():
    """Generate all figures"""
    import os
    os.makedirs('/root/.openclaw/workspace/paper/figures', exist_ok=True)
    
    print("="*50)
    print("Generating figures for UFT paper...")
    print("="*50)
    
    fig_spectral_dimension()
    fig_polarizations()
    fig_lisa_sensitivity()
    fig_black_hole_structure()
    fig_cosmology_timeline()
    
    print("="*50)
    print("All figures generated successfully!")
    print("="*50)

if __name__ == "__main__":
    main()
