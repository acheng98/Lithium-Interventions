import matplotlib.pyplot as plt
import numpy as np

size = 6
policy = 3

# Create figure and subplots
fig, axes = plt.subplots(1, size, figsize=(size*1.5, size), sharey=True)

x = np.linspace(0, 4, policy+3)
x = x[1:-1]

# Random seed for reproducibility
np.random.seed(42)

# Custom baselines for each subplot
baselines = [0, -3.5, 2, 4, -1, 1.5]

# Generate lollipop data for each subplot
for i, ax in enumerate(axes):
    baseline = baselines[i]
    y = np.random.randint(-5, 5, size=policy)  # values can be above or below the baseline
    y = np.append(0, y)

    ax.axhline(baseline, color='gray', linewidth=1)

    markers = ['o', 's', '^', 'D']
    colors = ['blue', 'green', 'orange', 'red']
    
     # Plot lollipops from custom baseline
    for i, (xi, yi) in enumerate(zip(x, y)):
        ax.vlines(xi, baseline, baseline + yi, color='gray')
        ax.plot(xi, baseline + yi, marker=markers[i % len(markers)], color=colors[i % len(colors)], markersize=10)

    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.set_xlim(0, 4)
    ax.set_ylim(-12, 12)

plt.tight_layout()
plt.show()