"""Knowledge base and offline educational repository for WaterWise AI.

Provides structured municipal water engineering concepts, process workflows,
glossary definitions, and reviewed offline answers for zero-credential learning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TopicModule:
    """Represents a major educational pillar in the learning center."""
    id: str
    title: str
    subtitle: str
    icon_name: str
    summary: str
    diagram_ascii: str
    key_stages: list[dict[str, str]]
    faq: list[dict[str, str]]
    sample_prompt: str


TOPIC_TREATMENT = TopicModule(
    id="treatment",
    title="Water Treatment Process",
    subtitle="From Raw Surface & Groundwater to Potable Drinking Water",
    icon_name="treatment",
    summary=(
        "Municipal water treatment is a multi-barrier engineering process designed to "
        "remove debris, suspended solids, harmful pathogens, and chemical contaminants. "
        "The exact sequence depends on source water quality, local regulations, and plant design."
    ),
    diagram_ascii=(
        "Raw Water Source (River/Lake/Aquifer)\n"
        "      │\n"
        "      ▼\n"
        "1. Screening & Intake (Removes large debris & vegetation)\n"
        "      │\n"
        "      ▼\n"
        "2. Coagulation & Rapid Mix (Alum/polymers neutralize particles)\n"
        "      │\n"
        "      ▼\n"
        "3. Flocculation (Slow stirring aggregates particles into 'floc')\n"
        "      │\n"
        "      ▼\n"
        "4. Clarification / Sedimentation (Heavy floc settles by gravity)\n"
        "      │\n"
        "      ▼\n"
        "5. Filtration (Granular media: sand, gravel, anthracite, GAC)\n"
        "      │\n"
        "      ▼\n"
        "6. Disinfection & Residual (Chlorine, chloramines, UV, ozone)\n"
        "      │\n"
        "      ▼\n"
        "7. Clearwell Storage & Distribution (Pressurized delivery network)"
    ),
    key_stages=[
        {
            "name": "1. Intake & Coarse Screening",
            "desc": "Water is extracted from rivers, lakes, or aquifers. Metal bar screens catch leaves, twigs, trash, and fish before water reaches pumps.",
        },
        {
            "name": "2. Coagulation",
            "desc": "Coagulant chemicals (such as aluminum sulfate or ferric chloride) are rapidly blended to neutralize negative electrostatic charges on colloidal silt and clay.",
        },
        {
            "name": "3. Flocculation",
            "desc": "Gentle, slow mixing paddles cause microscopic destabilized particles to collide, forming visible, heavier clusters known as floc.",
        },
        {
            "name": "4. Sedimentation / Settling",
            "desc": "Water flows into quiet basins where dense floc settles to the floor under gravity as sludge, leaving clarified water on top.",
        },
        {
            "name": "5. Multi-Media Filtration",
            "desc": "Water passes downward through beds of graded sand, anthracite coal, and gravel to filter out remaining microscopic suspended matter and parasites.",
        },
        {
            "name": "6. Disinfection",
            "desc": "Disinfectants (chlorine, chloramine, or UV light) destroy pathogenic bacteria, viruses, and amoebae. A controlled chemical residual is maintained to protect pipes.",
        },
    ],
    faq=[
        {
            "q": "Why does tap water sometimes smell slightly like chlorine?",
            "a": "Utilities maintain a small, harmless disinfectant residual (typically 0.2 to 2.0 mg/L) throughout distribution mains to prevent bacterial regrowth inside underground pipes. Letting water sit in an open pitcher allows chlorine to dissipate naturally.",
        },
        {
            "q": "Does clear water mean it is safe to drink?",
            "a": "No. Many dangerous microbial pathogens (Cryptosporidium, Giardia, E. coli) and dissolved chemical contaminants (lead, arsenic, nitrates) are completely invisible, odorless, and tasteless. Proper municipal filtration and testing are essential.",
        },
    ],
    sample_prompt="Explain the water treatment process.",
)

TOPIC_DISTRIBUTION = TopicModule(
    id="distribution",
    title="Water Distribution Networks",
    subtitle="Pumps, Mains, Storage Reservoirs & Hydraulic Pressure",
    icon_name="distribution",
    summary=(
        "Once treated, drinking water travels through hundreds or thousands of kilometers of "
        "interconnected pipes, booster stations, and elevated storage reservoirs to reach households "
        "at steady hydraulic pressure."
    ),
    diagram_ascii=(
        "Treatment Plant Clearwell\n"
        "      │\n"
        "      ▼ (High-Service High-Capacity Pumps)\n"
        "Transmission Mains (Large diameter 600mm–1800mm pipelines)\n"
        "      ├───► Elevated Storage Reservoirs / Water Towers (Pressure balancing)\n"
        "      │\n"
        "      ▼\n"
        "Distribution Mains (Grid network under streets, 150mm–400mm)\n"
        "      ├───► District Metered Areas (DMA & Pressure Reducing Valves)\n"
        "      │\n"
        "      ▼\n"
        "Service Connections (Ferrules, curb stops, household meters)\n"
        "      │\n"
        "      ▼\n"
        "Household Plumbing & Taps"
    ),
    key_stages=[
        {
            "name": "1. High-Service Pump Stations",
            "desc": "Powerful centrifugal pumps lift treated water out of plant storage clearwells and pressurize large-diameter transmission pipelines.",
        },
        {
            "name": "2. Transmission Mains",
            "desc": "Arterial steel, ductile iron, or prestressed concrete pipes that transport huge volumes across city zones without direct consumer connections.",
        },
        {
            "name": "3. Elevated Storage Towers & Balancing Tanks",
            "desc": "Towers store water during low-demand night hours and release it during morning peaks, using natural hydrostatic head (gravity) to maintain uniform network pressure.",
        },
        {
            "name": "4. Distribution Grid & Looping",
            "desc": "Pipes beneath city streets are interconnected in looped grids rather than dead-ends, ensuring redundant flow paths and preventing stagnant water pockets.",
        },
        {
            "name": "5. Pressure Management & PRVs",
            "desc": "Pressure Reducing Valves (PRVs) divide the city into topographic pressure zones, preventing burst pipes in low valleys while sustaining pressure on ridges.",
        },
    ],
    faq=[
        {
            "q": "Why do municipal supply schedules exist in some regions?",
            "a": "In intermittent supply networks or water-stressed municipalities, water is released during scheduled time slots by zones. Engineers use zone valves to fill localized storage tanks sequentially when source water or pumping capacity cannot meet continuous peak demand.",
        },
        {
            "q": "What happens if a major transmission pipe breaks?",
            "a": "Crews isolate the damaged pipe section using gate valves. Looped distribution networks often allow water to be routed around the break from another direction while emergency repairs are made.",
        },
    ],
    sample_prompt="How does water distribution work?",
)

TOPIC_PRESSURE = TopicModule(
    id="pressure",
    title="Water Pressure Issues & Dynamics",
    subtitle="Understanding Hydraulic Head, Friction, Elevation, and Restrictions",
    icon_name="pressure",
    summary=(
        "Water pressure is the force driving water through pipes and fixtures, measured in PSI "
        "or Bar. Pressure is governed by hydraulic elevation differences, pipe friction, peak consumer demand, "
        "and physical mechanical restrictions."
    ),
    diagram_ascii=(
        "Elevated Tower / Pumping Station\n"
        "    │\n"
        "    ├──► Static Head = Elevation Difference (0.433 PSI per foot of elevation)\n"
        "    │\n"
        "    ▼\n"
        "Flow Through Pipes (Dynamic Head Losses):\n"
        "    ├── Friction losses in aging, corroded, or undersized pipes\n"
        "    ├── High simultaneous demand (morning rush hours: 6 AM - 9 AM)\n"
        "    ├── Pressure Reducing Valve (PRV) miscalibration or failure\n"
        "    ├── Distribution main leaks or ongoing municipal maintenance\n"
        "    └── Household aerator clogging or closed main shutoff valve"
    ),
    key_stages=[
        {
            "name": "1. Topographic Elevation Differences",
            "desc": "Every 1 foot of elevation gain adds ~0.433 PSI of hydrostatic head. Homes situated on hills naturally experience lower pressure, while low valley areas experience higher pressure.",
        },
        {
            "name": "2. Peak Hour Fluctuations",
            "desc": "During peak morning hours (6:00 AM - 9:00 AM), thousands of households simultaneously open showers and appliances, increasing flow velocity and causing dynamic friction pressure drops across mains.",
        },
        {
            "name": "3. Pipe Scale & Mineral Encrustation",
            "desc": "Aging unlined iron pipes build up tuberculation (rust ridges) and mineral scale over decades, constricting internal diameters and choking water flow.",
        },
        {
            "name": "4. Household Valve & Aerator Restrictions",
            "desc": "A partially closed street curb stop valve, clogged faucet aerators, or failing household Pressure Regulating Valve (PRV) often cause localized low pressure in a single home.",
        },
    ],
    faq=[
        {
            "q": "How can I tell if low pressure is municipal or internal?",
            "a": "Check multiple faucets. If only one faucet has weak flow, the aerator or supply line is clogged. If the entire house is low, check if neighbors are experiencing the same issue. If neighbors have normal pressure, your household PRV or main shutoff valve is likely restricted.",
        },
        {
            "q": "What is water hammer?",
            "a": "A loud banging noise caused when a tap or appliance valve closes abruptly. The moving water column suddenly halts, sending a hydraulic shockwave back through the plumbing.",
        },
    ],
    sample_prompt="What causes low water pressure?",
)

TOPIC_CONSERVATION = TopicModule(
    id="conservation",
    title="Water Conservation Guidelines",
    subtitle="Household Efficiency, Leak Detection, and Community Stewardship",
    icon_name="conservation",
    summary=(
        "Water conservation protects shared aquatic ecosystems, reduces treatment energy consumption, "
        "lowers utility bills, and builds community resilience against droughts and seasonal shortages."
    ),
    diagram_ascii=(
        "Household Water Efficiency Hierarchy:\n"
        "1. Leak Detection (Toilets & Faucets: silent flapper leaks waste ~750 L/day)\n"
        "2. Fixture Efficiency (Aerators, low-flow showerheads, dual-flush toilets)\n"
        "3. Behavioral Practices (Short showers, full laundry loads, shut tap while brushing)\n"
        "4. Outdoor & Landscape (Drip irrigation, xeriscaping, mulch, rainwater harvesting)\n"
        "5. Greywater Reuse (Reusing non-toilet rinse water for non-edible landscape)"
    ),
    key_stages=[
        {
            "name": "1. Silent Leak Detection",
            "desc": "Drop food coloring in your toilet tank without flushing. If color seeps into the bowl within 15 minutes, the rubber flapper valve is worn and leaking hundreds of liters daily.",
        },
        {
            "name": "2. High-Efficiency Aerators & Fixtures",
            "desc": "Standard taps flow at 8-10 liters/min; installing WaterSense aerators cuts flow to 3.8-5 liters/min without sacrificing perceived pressure.",
        },
        {
            "name": "3. Rainwater Harvesting",
            "desc": "Collecting rooftop runoff into rain barrels or recharge wells reduces stormwater runoff and supplies free irrigation water for gardens.",
        },
        {
            "name": "4. Native Landscaping (Xeriscaping)",
            "desc": "Replacing thirsty grass lawns with drought-tolerant indigenous shrubs, trees, and mulch can cut outdoor household water consumption by over 50%.",
        },
    ],
    faq=[
        {
            "q": "How much water does a dripping faucet waste?",
            "a": "A tap leaking just one drop per second wastes over 3,000 gallons (11,000+ liters) of purified drinking water every year.",
        },
        {
            "q": "How does water conservation save electricity?",
            "a": "Water utilities are among the largest electricity consumers in municipalities due to raw water pumping, deep aeration, ozone systems, and high-pressure distribution mains. Saving water directly conserves grid energy.",
        },
    ],
    sample_prompt="What are some water conservation tips?",
)

TOPICS: list[TopicModule] = [
    TOPIC_TREATMENT,
    TOPIC_DISTRIBUTION,
    TOPIC_PRESSURE,
    TOPIC_CONSERVATION,
]

# Reviewed offline answers for zero-credential / fallback learning
OFFLINE_ANSWERS: dict[str, str] = {
    "Explain the water treatment process.": """### Water Treatment Process Overview

**Simple Explanation**  
Municipal water treatment turns raw river, lake, or groundwater into safe, crystal-clear drinking water by progressively removing floating debris, microscopic mud, and harmful germs.

**How It Works (Step-by-Step)**
1. **Intake & Screening**: Large bar screens stop river branches, leaves, and plastic debris.
2. **Coagulation**: Harmless minerals like alum are flash-mixed into the water. This neutralizes the electrostatic charges that keep fine clay and silt particles suspended.
3. **Flocculation**: Large paddles gently stir the water, allowing micro-particles to bind into sticky clumps called *floc*.
4. **Sedimentation**: The water sits in giant, quiet clarifying basins. Heavy floc sinks to the floor under gravity as settled sludge.
5. **Filtration**: Water passes down through beds of granular activated carbon, silica sand, and gravel to trap microscopic contaminants.
6. **Disinfection**: A controlled amount of chlorine, chloramine, or ultraviolet (UV) radiation destroys remaining bacteria and viruses. A small disinfectant residual remains in the water to keep underground pipes clean.
7. **Storage & Pumping**: Clean water enters sealed clearwells before high-power pumps send it through city pipes.

**Why It Matters**  
Treating water with multiple independent barriers prevents deadly waterborne diseases like cholera, typhoid, and cryptosporidiosis, protecting entire communities.

**Key Takeaway**  
Each treatment stage handles a specific contaminant scale—from visible debris to invisible microbes—ensuring the water exiting the plant meets strict national drinking water standards.
*(Note: This is an offline educational reference summary).*""",

    "How does water distribution work?": """### Water Distribution Systems

**Simple Explanation**  
A water distribution system is an underground highway of pressurized pipes, pumps, and water towers that delivers treated water straight to your household tap.

**How It Works**
1. **Pumping Stations**: Massive centrifugal pumps push purified water out of plant reservoirs into huge transmission pipelines (mains up to 1.5 meters wide).
2. **Elevated Water Towers**: Water is pumped up into elevated tanks. When consumer demand spikes, gravity pulls the water down naturally, sustaining steady pressure without straining pumps.
3. **Looped Street Mains**: Under neighborhood streets, pipes are interconnected in grid loops. Looping prevents stagnant dead-ends and ensures water can flow from multiple paths if a pipe breaks.
4. **Pressure Management (PRVs)**: Valves reduce pressure in valley areas so high hydrostatic pressure doesn't rupture household plumbing.
5. **Service Lateral & Meter**: A small pipe branches off the street main, passing through an emergency shutoff curb valve and a meter before entering your building.

**Why It Matters**  
Maintaining continuous pressure prevents backflow contamination. If pressure drops below atmospheric levels, groundwater or soil contaminants could be sucked into leaky pipe joints.

**Key Takeaway**  
Water distribution relies on a delicate balance of mechanical pumping and natural gravitational hydrostatic head to keep thousands of taps flowing simultaneously.
*(Note: This is an offline educational reference summary).*""",

    "What causes low water pressure?": """### Causes of Low Water Pressure

**Simple Explanation**  
Low water pressure occurs when the hydraulic push driving water through your plumbing is choked by friction, high neighborhood demand, elevation differences, or mechanical blockages.

**How It Works & Common Causes**
1. **Topography & Elevation**: Homes built on higher hills experience lower natural hydrostatic head (water loses ~0.43 PSI per foot of elevation).
2. **Peak Hour Demand**: When thousands of residents shower, run laundry, and water gardens between 6:00 AM and 9:00 AM, high water velocity causes steep friction losses in mains.
3. **Aging Pipes & Corrosion**: Decades of mineral scale or rust (tuberculation) narrow pipe interiors, severely throttling flow capacity.
4. **Pressure Reducing Valve (PRV) Faults**: If a household or street PRV is misadjusted or jammed, output pressure drops dramatically.
5. **Localized Restrictions**: Clogged faucet aerators, half-closed private shutoff valves, or hidden water heater scale can create low pressure in an isolated home.

**Why It Matters**  
Diagnosing whether low pressure affects your whole neighborhood or just a single tap helps determine whether the utility needs to inspect mains or if a private plumber is needed.

**Key Takeaway**  
Before assuming a municipal issue, test multiple faucets and ask immediate neighbors. If only your house is affected, the restriction is likely within your own private plumbing.
*(Note: This is an offline educational reference summary).*""",

    "What are some water conservation tips?": """### Water Conservation Guidelines

**Simple Explanation**  
Conserving water means eliminating silent household leaks, using efficient fixtures, and adopting thoughtful daily habits to protect shared water resources and save energy.

**Actionable Strategies**
1. **Detect Silent Toilet Leaks**: Place 4-5 drops of food coloring in the toilet tank without flushing. If color enters the bowl within 15 minutes, your flapper valve is leaking up to 750 liters a day.
2. **Install Low-Flow Aerators**: Modern faucet aerators reduce flow from 9 liters/min down to 4 liters/min with zero noticeable loss in cleaning force.
3. **Shorten Showers**: Reducing shower duration by just 3 minutes saves over 25 liters of treated hot water per person daily.
4. **Audit Outdoor Watering**: Water lawns and gardens only before 8:00 AM or after sunset to minimize evaporation losses. Consider drip irrigation and native drought-resistant plants.
5. **Full Appliance Loads**: Run dishwashers and washing machines only when completely full, utilizing eco-cycles whenever possible.

**Why It Matters**  
Pumping and treating municipal water consumes vast amounts of electricity. Saving treated water directly lowers carbon emissions, shrinks utility bills, and preserves rivers and aquifers.

**Key Takeaway**  
Fixing small, invisible leaks produces the single largest water reduction for most residential properties.
*(Note: This is an offline educational reference summary).*""",
}


GLOSSARY: list[dict[str, str]] = [
    {"term": "Potable Water", "def": "Water that is wholesome, free of pathogenic bacteria and harmful chemicals, and safe for human drinking and cooking."},
    {"term": "Turbidity", "def": "A measure of the cloudiness or haziness of water caused by suspended colloidal particles, measured in Nephelometric Turbidity Units (NTU)."},
    {"term": "Coagulation", "def": "The chemical treatment process where coagulant chemicals (like alum) destabilize charges on suspended silt particles."},
    {"term": "Flocculation", "def": "The slow mechanical mixing process that aggregates destabilized particles into larger, settleable clusters (floc)."},
    {"term": "Static Head", "def": "The vertical height of a water column above a point, creating natural pressure due to gravity (approx 0.433 PSI per vertical foot)."},
    {"term": "Dynamic Pressure", "def": "The actual pressure measured in a pipe when water is in motion, which is lower than static pressure due to friction."},
    {"term": "PRV (Pressure Reducing Valve)", "def": "An automatic hydraulic valve installed in pipes to restrict high upstream pressure down to a safe downstream level."},
    {"term": "Backflow Prevention", "def": "Mechanical check valves designed to prevent non-potable water or contaminants from being siphoned back into public drinking mains."},
    {"term": "SCADA", "def": "Supervisory Control and Data Acquisition: industrial computer systems used by water engineers to monitor tank levels, pump status, and flow rates."},
    {"term": "District Metered Area (DMA)", "def": "A hydraulically isolated sector of a city distribution network where inflows and outflows are continuously metered to detect leaks."},
]


def get_curated_answer(question: str) -> str | None:
    """Return a curated offline answer if the question matches standard prompts."""
    q_clean = question.strip()
    for key, ans in OFFLINE_ANSWERS.items():
        if key.lower() == q_clean.lower():
            return ans
    return None
