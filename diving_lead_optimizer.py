import numpy as np
import matplotlib.pyplot as plt
from freediving import plot_net_force_kgf

def energy_use(params, depth, lung_condition, plot=False):
    # Step 1: Get depth and net force curves
    depths, net_force_curves = plot_net_force_kgf(params, plot=False)
    depths = np.array(depths)  # Ensure NumPy array
    net_forces = np.array(net_force_curves[lung_condition])

    # Step 2: Interpolate to match the target depth
    depth_indices = depths <= depth
    relevant_depths = depths[depth_indices]
    relevant_forces = net_forces[depth_indices]

    # Step 3: Initialize arrays for energy deltas and cumulative energy
    energy_deltas = []
    combined_depths = [relevant_depths[0]]  # Start with the initial depth
    direction_flags = []  # Track whether going down (-1) or up (+1)

    # Downward motion
    for i in range(len(relevant_depths) - 1):
        force = relevant_forces[i] * 9.81  # Convert kgf to Newtons
        distance = relevant_depths[i + 1] - relevant_depths[i]

        if force > 0:  # Force opposes downward motion
            work_done = force * abs(distance)
        else:
            work_done = 0

        energy_deltas.append(work_done)
        combined_depths.append(relevant_depths[i + 1])
        direction_flags.append(-1)  # Going down

    # Upward motion
    for i in range(len(relevant_depths) - 1, 0, -1):
        force = relevant_forces[i] * 9.81  # Convert kgf to Newtons
        distance = relevant_depths[i] - relevant_depths[i - 1]

        if force < 0:  # Force opposes upward motion
            work_done = abs(force * distance)
        else:
            work_done = 0

        energy_deltas.append(work_done)
        combined_depths.append(relevant_depths[i - 1])
        direction_flags.append(1)  # Going up

    # Convert to Wh and calculate cumulative energy
    energy_deltas_wh = np.array(energy_deltas) / 3600  # Convert to Wh
    cumulative_energy_wh = np.concatenate([[0], np.cumsum(energy_deltas_wh)])  # Start with zero energy

    # Plot if requested
    if plot:
        # Split the data into descent and ascent for coloring
        down_indices = [i for i, flag in enumerate(direction_flags) if flag == -1]
        up_indices = [i for i, flag in enumerate(direction_flags) if flag == 1]

        plt.figure(figsize=(8, 6))
        # Plot descent in red
        plt.plot(
            np.array(cumulative_energy_wh)[down_indices + [down_indices[-1] + 1]],
            np.array(combined_depths)[down_indices + [down_indices[-1] + 1]],
            color="red",
            label="Descent",
        )
        # Plot ascent in blue
        plt.plot(
            np.array(cumulative_energy_wh)[up_indices + [up_indices[-1] + 1]],
            np.array(combined_depths)[up_indices + [up_indices[-1] + 1]],
            color="blue",
            label="Ascent",
        )
        plt.xlabel("Cumulative Energy Usage (Wh)")
        plt.ylabel("Depth (m)")
        plt.title("Cumulative Energy Usage vs Depth")
        plt.axhline(0, color="black", linewidth=0.5, linestyle="--")
        plt.axvline(0, color="black", linewidth=0.5, linestyle="--")
        plt.gca().invert_yaxis()  # Depth positive downward
        plt.grid()
        plt.legend()
        plt.savefig("cumulative_energy_usage.pdf", dpi=400, bbox_inches="tight")
        plt.savefig("cumulative_energy_usage.png", dpi=400, bbox_inches="tight")
        plt.show()

    return cumulative_energy_wh[-1]




def energy_vs_weight(params, depth, weight_list=None, plot=False):
    lung_conditions = ["full_lung", "medium_lung", "empty_lung"]
    if weight_list is not None:
        weights = weight_list
    else:
        weights = np.arange(0, 12, 0.2)  # Lead weights from 0 to 12 kg in 0.05 kg steps
    results = {}

    for lung_condition in lung_conditions:
        energies = []
        for weight in weights:
            # Update params to include the lead weight
            params_with_weight = params.copy()
            params_with_weight["lead_weight"] = weight

            # Calculate energy expenditure
            energy = energy_use(params_with_weight, depth, lung_condition, plot=False)
            energies.append(energy)

        # Convert energies to a numpy array for interpolation
        energies = np.array(energies)

        # Find the index of the minimum energy
        min_idx = np.argmin(energies)

        # Ensure the minimum is not on the boundary of the array
        if min_idx == 0 or min_idx == len(weights) - 1:
            optimal_weight = weights[min_idx]
            min_energy = energies[min_idx]
        else:
            # Use quadratic interpolation with three points
            x1, x2, x3 = weights[min_idx - 1:min_idx + 2]
            y1, y2, y3 = energies[min_idx - 1:min_idx + 2]

            # Fit a quadratic polynomial: y = ax^2 + bx + c
            coeffs = np.polyfit([x1, x2, x3], [y1, y2, y3], 2)
            a, b, c = coeffs

            # Vertex of the parabola (optimal weight)
            optimal_weight = -b / (2 * a)
            # Minimum energy at the vertex
            min_energy = np.polyval(coeffs, optimal_weight)

        # Store results
        results[lung_condition] = {
            "weights": list(weights),
            "energies": list(energies),
            "optimal_weight": optimal_weight,
            "minimum_energy": min_energy,
        }

    # Plot the results
    if plot:
        plt.figure(figsize=(5, 5))
        max_energy = max(
            max(results[lung_condition]["energies"]) for lung_condition in lung_conditions
        )
        plt.ylim([0, max_energy])

        for lung_condition in lung_conditions:
            weights = results[lung_condition]["weights"]
            energies = results[lung_condition]["energies"]
            optimal_weight = results[lung_condition]["optimal_weight"]
            minimum_energy = results[lung_condition]["minimum_energy"]

            energies = np.array(energies)
            weights  = np.array(weights)

            # Plot the energy curve
            plt.plot(weights, energies, label=f"{lung_condition.capitalize()}")

            # Annotate the optimal point with an arrow
            plt.annotate(
                f"{optimal_weight:.1f} kg",
                xy=(optimal_weight, minimum_energy),
                xytext=(optimal_weight + 0.2, minimum_energy + 0.05),  # Adjusting vertical offset
                arrowprops=dict(facecolor="black", arrowstyle="->", lw=0.8),
                fontsize=9,
                ha="center",
            )

        plt.xlabel("Lead Weight (kg)")
        plt.ylabel("Total Energy Usage (Wh)")
        plt.title(f"Energy Usage vs Lead Weight for {depth}m Dive")
        plt.axhline(0, color="black", linewidth=0.5, linestyle="--")
        plt.axvline(0, color="black", linewidth=0.5, linestyle="--")
        plt.xlim([0, 6])
        plt.ylim([0, np.nanmax(energies[weights < 6])])
        plt.grid()
        plt.legend()
        plt.savefig("energy_vs_weight.pdf", dpi=400, bbox_inches="tight")
        plt.savefig("energy_vs_weight.png", dpi=400, bbox_inches="tight")
        plt.show()

    return results



from tqdm import tqdm  # For the progress bar

def optimal_weight_vs_depth(params, max_depth=50, plot=True):
    depths = np.arange(1, max_depth + 1, 0.5)  # Depths from 0 to max_depth in 2m steps
    lung_conditions = ["full_lung", "medium_lung", "empty_lung"]
    optimal_weights = {condition: [] for condition in lung_conditions}

    # Styles for lung conditions
    styles = {
        "full_lung": {"linestyle": "-", "label": f"Full Lung ({params['lung_volumes']['full_lung']} L)"},
        "medium_lung": {"linestyle": "--", "label": f"Medium Lung ({params['lung_volumes']['medium_lung']} L)"},
        "empty_lung": {"linestyle": ":", "label": f"Empty Lung ({params['lung_volumes']['empty_lung']} L)"},
    }

    # Calculate the optimal weight for each depth with a progress bar
    with tqdm(total=len(depths), desc="Calculating optimal weights", unit="depth") as pbar:
        for depth in depths:
            results = energy_vs_weight(params, depth, plot=False)
            for lung_condition in lung_conditions:
                optimal_weights[lung_condition].append(results[lung_condition]["optimal_weight"])
            pbar.update(1)  # Update the progress bar

    # Plot the results
    if plot:
        plt.figure(figsize=(5, 5))

        # Add wavy water surface
        x_limits = [0, 10]  # Adjust based on weight range
        x_waves = np.linspace(x_limits[0], x_limits[1], 200)
        y_waves = 1.0 * np.sin(2 * np.pi * x_waves / 5)

        # Create gradient shading for the ocean below the wavy surface
        gradient_depths = np.linspace(0, max_depth, 500)  # Depth levels for gradient
        gradient_colors = plt.cm.Blues(np.linspace(0.2, 0.95, len(gradient_depths)))  # Gradient colors


        # Plot gradient shading
        for i in range(len(gradient_depths) - 1):
            plt.fill_between(
                x_waves,
                y_waves + gradient_depths[i],  # Top boundary: wavy surface + current depth
                max_depth,  # Bottom boundary: deepest depth (e.g., 100 m)
                color=gradient_colors[i],  # Gradient color for this level
                zorder=0,
            )


        # Plot lung condition curves
        for lung_condition in lung_conditions:
            plt.plot(
                optimal_weights[lung_condition],
                depths,
                styles[lung_condition]["linestyle"],
                label=styles[lung_condition]["label"],
                color="black",
                zorder=9,
            )

        # Formatting
        plt.ylim([-10, max_depth])
        plt.xlim([0,10])
        plt.gca().invert_yaxis()  # Depth positive downward
        plt.xlabel("Optimal Lead Weight (kg)")
        plt.ylabel("Depth (m)")
        plt.title("Optimal Lead Weight vs Depth")
        plt.axhline(0, color="black", linewidth=0.5, linestyle="--", zorder=10)  # Surface line
        plt.axvline(0, color="black", linewidth=0.5, linestyle="--", zorder=10)  # Neutral weight line
        plt.grid()
        plt.legend()
        plt.savefig("optimal_weight_vs_depth_with_water.pdf", dpi=400, bbox_inches="tight")
        plt.savefig("optimal_weight_vs_depth_with_water.png", dpi=400, bbox_inches="tight")
        plt.show()

    return optimal_weights



# Example usage
if __name__ == "__main__":
    from freediving import params
    # energy_vs_weight(params, depth=30, weight_list=np.linspace(0,10,1000), plot=True)
    max_depth = 50  # Maximum depth to calculate
    results = optimal_weight_vs_depth(params, max_depth=max_depth, plot=True)

    # Print the results for each lung condition
    for lung_condition, weights in results.items():
        print(f"Lung Condition: {lung_condition}")
        for depth, weight in zip(range(max_depth + 1), weights):
            print(f"  Depth: {depth} m, Optimal Weight: {weight:.1f} kg")
