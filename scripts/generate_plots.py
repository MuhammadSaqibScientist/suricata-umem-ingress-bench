#!/usr/bin/env python3
"""
generate_plots.py - Generate publication-quality figures for AF_PACKET vs AF_XDP benchmark.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Set academic plotting style
sns.set_theme(style="whitegrid", font="DejaVu Sans")
plt.rcParams.update({
    'font.size': 11,
    'axes.labelsize': 12,
    'axes.titlesize': 13,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 14
})

def main():
    print("[+] Loading benchmark summary...")
    df = pd.read_csv('benchmark_summary.csv')

    # Avoid log(0) issues by replacing 0 or negative drop rates with a small floor value for plotting
    df['plot_drop_rate'] = df['drop_rate_pct'].apply(lambda x: max(x, 0.01))

    # Create figure with 2 subplots (Drop Rate vs Load & Ring Size Impact)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # --- Plot 1: Drop Rate vs Offered Load ---
    sns.lineplot(
        data=df,
        x='offered_load_pps',
        y='plot_drop_rate',
        hue='mode',
        style='mode',
        markers=True,
        dashes=False,
        linewidth=2.5,
        markersize=8,
        ax=axes[0]
    )
    axes[0].set_title('Packet Drop Rate vs. Offered Load')
    axes[0].set_xlabel('Offered Load (Packets/sec)')
    axes[0].set_ylabel('Drop Rate (%) [Log Scale]')
    axes[0].set_yscale('log')
    axes[0].legend(title='Capture Framework')

    # --- Plot 2: Drop Rate vs Ring Size (at Max Load) ---
    max_load = df['offered_load_pps'].max()
    max_load_df = df[df['offered_load_pps'] == max_load]
    
    sns.barplot(
        data=max_load_df,
        x='ring_size',
        y='plot_drop_rate',
        hue='mode',
        ax=axes[1],
        palette='muted'
    )
    axes[1].set_title(f'Impact of Ring Size on Drops at Max Load ({max_load:,} pps)')
    axes[1].set_xlabel('Ring Buffer Size')
    axes[1].set_ylabel('Drop Rate (%)')
    axes[1].set_yscale('log')
    axes[1].legend(title='Capture Framework')

    plt.tight_layout()
    
    # Save as high-resolution PNG and Vector PDF for LaTeX paper inclusion
    plt.savefig('ingress_performance_comparison.png', dpi=300)
    plt.savefig('ingress_performance_comparison.pdf', format='pdf')
    print("[✔] Successfully generated updated figures:")
    print("    - ingress_performance_comparison.png")
    print("    - ingress_performance_comparison.pdf")

if __name__ == '__main__':
    main()
