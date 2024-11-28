import matplotlib.pyplot as plt
import numpy as np

def calculate_seawater_density(salinity, temperature):
    """Estimate seawater density (g/cm^3) based on salinity (ppt) and temperature (°C)."""
    return 1.000 + 0.0008 * salinity - 0.0003 * temperature


def get_salinity_and_density(water_type, temperature):
    """Return typical salinity and calculate density based on water type."""
    salinity = 35 if water_type == "sea" else 0
    return calculate_seawater_density(salinity, temperature) * 1000  # Convert to kg/m^3


def plot_net_force_kgf(params, plot=False):
    # Unpack configurable x and y limits
    x_limits = params["x_limits"]
    y_limits = params["y_limits"]

    # Calculate water density based on type and temperature
    params["seawater_density"] = get_salinity_and_density(
        params["water_type"], params["temperature"]
    )

    depths = np.linspace(0, params["y_limits"][0], 500)  # Positive below surface
    wetsuit_compressibility_factor = params["wetsuit_compressibility_factor"]/100  # convert to percentage shink per meter depth (6% every 10 meters, where air is 50% every 10 meters)

    styles = {
        "full_lung": {"linestyle": "-", "label": f"Full Lung ({params['lung_volumes']['full_lung']} L)"},
        "medium_lung": {"linestyle": "--", "label": f"Medium Lung ({params['lung_volumes']['medium_lung']} L)"},
        "empty_lung": {"linestyle": ":", "label": f"Empty Lung ({params['lung_volumes']['empty_lung']} L)"},
    }

    if plot:
        plt.figure(figsize=(6, 6))

    net_force_curves = {}

    for condition, lung_volume in params["lung_volumes"].items():
        net_forces_kgf = []
        for d in depths:
            if d < 0:  # Above surface: no buoyancy
                net_force_kgf = -params["mass"] - params["wetsuit_mass"]
            else:  # Submerged: apply physics
                lung_volume_cm3 = lung_volume * 1000  # Convert lung volume to cm^3
                rv = params["residual_volume"]  # Residual volume in cm^3
                lung_volume_at_depth = rv + (lung_volume_cm3 - rv) / (1 + d / 10)

                # Calculate displacement volumes
                volume_fat = params["mass"] * params["body_fat_percentage"] * 1000 / 0.9
                volume_lean = (params["mass"] * (1 - params["body_fat_percentage"])) * 1000 / 1.1

                # Incorporate wetsuit compressibility
                wetsuit_volume_surface = (params["wetsuit_mass"] * 1000) / params["wetsuit_density"]
                wetsuit_volume_at_depth = wetsuit_volume_surface * (1 - wetsuit_compressibility_factor * d)

                snorkel_volume = params["snorkel_mask_volume"]
                weight_volume = params["lead_weight"] / 11340  # Volume of lead in m^3

                # Total displacement volume includes lead volume (since it displaces water)
                total_displacement_volume = (
                    volume_fat / (1 + d * 0.1 / 100)
                    + volume_lean / (1 + d * 0.05 / 100)
                    + lung_volume_at_depth
                    + wetsuit_volume_at_depth
                    + snorkel_volume
                    + weight_volume * 1e6  # Add lead displacement (convert to cm^3)
                ) * 1e-6  # Convert total to m^3

                # Calculate forces
                F_buoyancy = total_displacement_volume * params["seawater_density"] * 9.81  # Buoyant force in N
                F_weight = (params["mass"] + params["wetsuit_mass"] + params["lead_weight"]) * 9.81  # Gravitational force in N
                net_force_kgf = (F_buoyancy - F_weight) / 9.81  # Convert to kgf

            net_forces_kgf.append(net_force_kgf)

        net_force_curves[condition] = net_forces_kgf

        # Plot net force vs. depth

        if plot:
            plt.plot(
                net_forces_kgf,
                depths,
                styles[condition]["linestyle"],
                label=styles[condition]["label"],
                color="black",
                zorder=9,
            )


    if plot:

        # Add wavy water surface
        x_waves = np.linspace(x_limits[0], x_limits[1], 1000)
        y_waves = 1.0 * np.sin(2 * np.pi * x_waves / 5)

        # Create gradient shading for the ocean below the wavy surface
        gradient_depths = np.linspace(0, params["y_limits"][0], 500)  # Depth levels for gradient
        gradient_colors = plt.cm.Blues(np.linspace(0.2, 0.95, len(gradient_depths)))  # Gradient colors

        # Plot gradient shading
        for i in range(len(gradient_depths) - 1):
            plt.fill_between(
                x_waves,
                y_waves + gradient_depths[i],  # Top boundary: wavy surface + current depth
                params["y_limits"][0],  # Bottom boundary: deepest depth (e.g., 100 m)
                color=gradient_colors[i],  # Gradient color for this level
                zorder=0,
            )

        # Add freefall shading below the wavy surface
        freefall_x = x_waves[x_waves <= 0]  # Restrict x to the freefall region (e.g., -5 to 0)
        freefall_y_top = y_waves[:len(freefall_x)]  # Corresponding y values for the same region

        plt.fill_between(
            freefall_x,
            freefall_y_top,         # Top boundary: wavy surface
            params["y_limits"][0],  # Bottom boundary: deepest depth (e.g., 100 m)
            color="red",
            alpha=0.4,
            zorder=7,
            label="Freefall",
        )

        # Formatting
        plt.gca().invert_yaxis()  # Invert y-axis to make depth positive downward
        yticks = np.arange(0, abs(params["y_limits"][0]) + 1, 10)  # Generate ticks at intervals of 10
        plt.yticks(yticks)  # Set the y-ticks
        plt.xlabel("Net Force (kgf)")
        plt.ylabel("Depth (m)")
        plt.title(f"Net Force vs Depth for Freediver (Lead Weight: {params['lead_weight']} kg)")
        plt.legend(loc="lower right")
        plt.grid()
        plt.xlim(x_limits)
        plt.ylim(y_limits)
        plt.savefig("example_result.pdf", dpi=400, bbox_inches="tight")
        plt.savefig("example_result.png", dpi=400, bbox_inches="tight")
        plt.show()


    return depths, net_force_curves



# Example parameters
params = {
    "mass": 70,  # mass of diver and glasses, excluding wetsuit and lead mass, in kg
    "height": 1.84,  # meters (for context only)
    "body_fat_percentage": 0.20,  # 0.22 is a fudge factor to ensure neutral buoyancy with hot spring water, real approximate fat percentage (13-15%) if waist 79 cm, neck 36 cm
    "lung_volumes": {
        "full_lung": 6.5,  # liters
        "medium_lung": 4.0,  # liters
        "empty_lung": 1.5,  # liters, close to residual volume
    },
    "residual_volume": 1.5 * 1000,  # Residual lung volume in cm^3
    "wetsuit_mass": 1.24,  # kg, actual measurement 1252g with some humidity
    "wetsuit_density": 0.24,  # g/cm^3, includes socks and/or gloves
    "snorkel_mask_volume": 150,  # cm^3
    "lead_weight": 0.0,  # kg
    "water_type": "sea",  # "sea" or "fresh"
    "temperature": 22,  # °C
    "wetsuit_compressibility_factor": 1.6, # % per meter, real world data suggests 1.7% to 1.3% per meter based on, ~0.33-0.45% of original volume at 40 m
    "x_limits": [-4, 8],
    "y_limits": [50, -10],
}

plot_net_force_kgf(params, plot=False)
