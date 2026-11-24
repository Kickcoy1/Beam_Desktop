import numpy as np


STEEL_SECTIONS = {
    "W8x10": {"E": 29000.0, "Ix": 30.8, "Sx": 7.81, "weight": 10.0},
    "W10x12": {"E": 29000.0, "Ix": 53.8, "Sx": 10.9, "weight": 12.0},
    "W12x26": {"E": 29000.0, "Ix": 204.0, "Sx": 33.4, "weight": 26.0},
    "W14x22": {"E": 29000.0, "Ix": 199.0, "Sx": 29.0, "weight": 22.0},
    "W16x26": {"E": 29000.0, "Ix": 301.0, "Sx": 38.4, "weight": 26.0},
    "W18x35": {"E": 29000.0, "Ix": 510.0, "Sx": 57.6, "weight": 35.0},
    "W21x44": {"E": 29000.0, "Ix": 843.0, "Sx": 81.6, "weight": 44.0},
    "W24x55": {"E": 29000.0, "Ix": 1350.0, "Sx": 114.0, "weight": 55.0},
}

LUMBER_SECTIONS = {
    "2x8": {"E": 1600.0, "Ix": 47.63, "Sx": 13.14},
    "2x10": {"E": 1600.0, "Ix": 98.93, "Sx": 21.39},
    "2x12": {"E": 1600.0, "Ix": 177.98, "Sx": 31.64},
}

STEEL_ORDER = list(STEEL_SECTIONS)
LUMBER_ORDER = list(LUMBER_SECTIONS)


def _clip_loads(span, point_loads, uniform_loads):
    points = []
    for load in point_loads:
        position = float(load["position"])
        magnitude = max(0.0, float(load["magnitude"]))
        if 0 <= position <= span:
            points.append({"magnitude": magnitude, "position": position})

    uniforms = []
    for load in uniform_loads:
        magnitude = max(0.0, float(load["magnitude"]))
        start = max(0.0, float(load["start"]))
        end = min(span, float(load["end"]))
        if end < start:
            start, end = end, start
            start = max(0.0, start)
            end = min(span, end)
        if end > start:
            uniforms.append({"magnitude": magnitude, "start": start, "end": end})
    return points, uniforms


def calculate(support, span, point_loads, uniform_loads, section_name,
              material, deflection_limit, include_recommendation=True):
    span = float(span)
    if not 4 <= span <= 40:
        raise ValueError("Span must be between 4 and 40 ft.")
    if section_name not in (STEEL_SECTIONS if material == "steel" else LUMBER_SECTIONS):
        raise KeyError(section_name)

    points, uniforms = _clip_loads(span, point_loads, uniform_loads)
    properties = (STEEL_SECTIONS if material == "steel" else LUMBER_SECTIONS)[section_name]

    total_load = sum(load["magnitude"] for load in points)
    load_moment = sum(load["magnitude"] * load["position"] for load in points)
    for load in uniforms:
        length = load["end"] - load["start"]
        total_load += load["magnitude"] * length
        load_moment += load["magnitude"] * length * (load["start"] + load["end"]) / 2

    if support == "simply-supported":
        left_reaction = total_load - load_moment / span
        right_reaction = load_moment / span
        reactions = {"left": left_reaction, "right": right_reaction,
                     "fixed": None, "fixed_moment": None}
        fixed_moment = None
    else:
        left_reaction = total_load
        fixed_moment = load_moment
        reactions = {"left": left_reaction, "right": None,
                     "fixed": left_reaction, "fixed_moment": fixed_moment}

    breaks = {0.0, span}
    for load in points:
        breaks.add(load["position"])
    for load in uniforms:
        breaks.add(load["start"])
        breaks.add(load["end"])
    breaks = sorted(value for value in breaks if 0 <= value <= span)

    sample = set(np.arange(0.0, span + 0.25, 0.25))
    sample.update(np.arange(0.0, span + 0.01, 0.01))
    sample.update(breaks)
    x = np.array(sorted(value for value in sample if 0 <= value <= span), dtype=float)

    if support == "simply-supported":
        shear = np.full_like(x, left_reaction)
        moment = left_reaction * x
    else:
        shear = np.full_like(x, left_reaction)
        moment = -fixed_moment + left_reaction * x

    for load in points:
        shear -= np.where(x >= load["position"], load["magnitude"], 0.0)
        moment -= np.where(
            x >= load["position"],
            load["magnitude"] * (x - load["position"]),
            0.0,
        )
    for load in uniforms:
        c = np.clip(x, load["start"], load["end"])
        active = c > load["start"]
        shear -= np.where(
            x > load["start"],
            load["magnitude"] * np.clip(x - load["start"], 0.0,
                                        load["end"] - load["start"]),
            0.0,
        )
        moment -= np.where(
            active,
            load["magnitude"] * (
                (c - load["start"]) * x
                - (c ** 2 - load["start"] ** 2) / 2
            ),
            0.0,
        )

    deflection = deflection_for_section(
        x, moment, span, support, properties["E"], properties["Ix"]
    )

    bending_stress = float(np.max(np.abs(moment)) * 12.0 / properties["Sx"])
    allowable_bending = 30.0 if material == "steel" else 0.900
    allowable_deflection = span * 12.0 / float(deflection_limit)
    max_deflection = float(np.max(np.abs(deflection)))
    bending_pass = bending_stress <= allowable_bending
    deflection_pass = max_deflection <= allowable_deflection

    moment_i = int(np.argmax(np.abs(moment)))
    deflection_i = int(np.argmax(np.abs(deflection)))
    shear_i = int(np.argmax(np.abs(shear)))

    recommendation = None
    if include_recommendation:
        recommendation = recommended_section(
            support, span, point_loads, uniform_loads, material, deflection_limit
        )

    return {
        "x": x,
        "shear": shear,
        "moment": moment,
        "deflection": deflection,
        "reactions": reactions,
        "bending_stress": bending_stress,
        "allowable_bending": allowable_bending,
        "allowable_deflection": allowable_deflection,
        "max_deflection": max_deflection,
        "bending_pass": bending_pass,
        "deflection_pass": deflection_pass,
        "both_pass": bending_pass and deflection_pass,
        "moment_extreme": float(moment[moment_i]),
        "moment_extreme_x": float(x[moment_i]),
        "deflection_extreme": float(deflection[deflection_i]),
        "deflection_extreme_x": float(x[deflection_i]),
        "shear_extreme": float(shear[shear_i]),
        "shear_extreme_x": float(x[shear_i]),
        "recommendation": recommendation,
    }


def deflection_for_section(x, moment, span, support, E, Ix):
    moment_in = moment * 12.0
    EI = E * Ix
    x_in = x * 12.0
    curvature = moment_in / EI
    dx = np.diff(x_in)

    theta_curve = np.concatenate(([0.0], np.cumsum(
        (curvature[:-1] + curvature[1:]) * dx / 2.0
    )))
    y_curve = np.concatenate(([0.0], np.cumsum(
        (theta_curve[:-1] + theta_curve[1:]) * dx / 2.0
    )))

    if support == "simply-supported":
        theta_zero = -y_curve[-1] / (span * 12.0)
        y = y_curve + theta_zero * x_in
    else:
        y = y_curve
    return y


def recommended_section(support, span, point_loads, uniform_loads, material,
                        deflection_limit):
    table = STEEL_SECTIONS if material == "steel" else LUMBER_SECTIONS
    names = STEEL_ORDER if material == "steel" else LUMBER_ORDER
    passing = []
    for name in names:
        result = calculate(
            support, span, point_loads, uniform_loads, name, material,
            deflection_limit, include_recommendation=False
        )
        if result["bending_pass"] and result["deflection_pass"]:
            passing.append(name)
    if not passing:
        return None
    if material == "lumber":
        return passing[0]
    return sorted(passing, key=lambda name:
                  (table[name]["weight"], -table[name]["Ix"]))[0]
