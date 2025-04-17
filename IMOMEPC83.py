import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- Configuration & Data ---

# Predefined Fuel Data (LHV in MJ/t, GFI in gCO2eq/MJ)
PREDEFINED_FUELS = {
    "HFO": {"LHV": 41000, "GFI": 91.00},
    "LNG": {"LHV": 49000, "GFI": 68.00},
    "B24": {"LHV": 41500, "GFI": 75.00},
    "e-Ammonia": {"LHV": 18600, "GFI": 3.00},
    "bio-Methanol": {"LHV": 19900, "GFI": 5.00},
}

# Reference GFI Value
REFERENCE_GFI = 93.3 # gCO2eq/MJ

# Reduction Targets (%) relative to Reference GFI
TARGET_REDUCTIONS = {
    # Year: (Base Target Reduction %, Direct Compliance Target Reduction %)
    2028: (4.0, 17.0),
    2029: (6.0, 19.0),
    2030: (8.0, 21.0),
    2031: (12.4, 25.4),
    2032: (16.8, 29.8),
    2033: (21.2, 34.2),
    2034: (25.6, 38.6),
    2035: (30.0, 43.0),
}
YEARS = list(TARGET_REDUCTIONS.keys())

# RU Prices ($/t CO2eq)
T1_FIXED_PRICE = 100.0 # Price for Tier 1 deficit
T2_FIXED_PRICE = 380.0 # Price for Tier 2 deficit (Fixed period)

# --- Streamlit App Layout ---

st.set_page_config(layout="wide")

# Use Markdown for potentially larger/bolder title if desired
st.markdown("<h1 style='text-align: center; color: #004c6d;'>IMO MEPC 83 - Two-tier GFI-linked pricing system</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center; color: grey;'>Cost and compliance calculator</h2>", unsafe_allow_html=True)


col1, col2 = st.columns([1, 1])

# --- Input Section ---
with col1:
    # Removed Input Method selector as it wasn't in the last screenshot
    # st.header("Input Method:")
    # input_method = st.radio("", ("Predefined Fuel", "Custom GFI"), label_visibility="collapsed", key="input_method")
    input_method = "Predefined Fuel" # Hardcoding based on UI look

    st.subheader("Fuel Type:") # Changed header level for visual hierarchy
    if input_method == "Predefined Fuel":
        fuel_options = list(PREDEFINED_FUELS.keys())
        # Default to bio-Methanol as per screenshot
        default_index_fuel = fuel_options.index("bio-Methanol") if "bio-Methanol" in fuel_options else 0
        fuel_type = st.radio("", fuel_options, index=default_index_fuel, horizontal=True, label_visibility="collapsed", key="fuel_type_radio")
        selected_fuel_data = PREDEFINED_FUELS[fuel_type]
        attained_lhv = selected_fuel_data["LHV"]
        attained_gfi = selected_fuel_data["GFI"]
        # Using st.markdown for potentially better formatting control
        st.markdown(f"<div style='background-color:#e8f0fe; padding: 10px; border-radius: 5px;'>Selected: <b>{fuel_type}</b> (LHV: {attained_lhv:,.1f} MJ/t | GFI: {attained_gfi:.2f} gCO₂eq/MJ)</div>", unsafe_allow_html=True)

    else: # Keep custom logic if needed, though hidden based on screenshot
        fuel_type = "Custom"
        attained_lhv = st.number_input("Fuel LHV (MJ/t)", value=41000.0, format="%.1f", key="custom_lhv")
        attained_gfi = st.number_input("Attained GFI (gCO₂eq/MJ)", value=91.00, format="%.2f", key="custom_gfi")
        st.info(f"Selected: Custom Fuel (LHV: {attained_lhv:,.1f} MJ/t | GFI: {attained_gfi:.2f} gCO₂eq/MJ)")

    # Header styling similar to screenshot
    st.markdown("### Tonnes Consumed:")
    # Use default from original image
    tonnes_consumed = st.number_input("", min_value=0.0, value=5000.0, step=100.0, format="%.2f", label_visibility="collapsed", key="tonnes_consumed")
    st.caption("per annum")


with col2:
    st.subheader("Pricing Assumptions:") # Changed header level
    # Use defaults from screenshot
    surplus_price = st.number_input("Assumed surplus unit (SU) trading price:", min_value=0.0, value=380.0, step=10.0, format="%.1f", key="surplus_price")
    st.caption("$/t CO₂eq (Revenue for performance better than Direct Compliance Target)")

    t1_ru_price_user = st.number_input("Tier 1 RU Price (2031+):", min_value=0.0, value=100.0, step=10.0, format="%.1f", key="t1_price_user")
    st.caption("$/t CO₂eq")

    t2_ru_price_user = st.number_input("Tier 2 RU Price (2031+):", min_value=0.0, value=360.0, step=10.0, format="%.1f", key="t2_price_user") # Changed default to 360.0
    st.caption("$/t CO₂eq")


# --- Calculation Button ---
# Add some space before the button
st.markdown("<br>", unsafe_allow_html=True)
calculate_button = st.button("Calculate and Plot Results") # Removed type="primary" to match screenshot style

# --- Output Section ---
st.divider()

results_col, plot_col = st.columns([1, 1.5]) # Adjust column ratios if needed

with results_col:
    st.subheader("Calculation Results") # Changed header level
    results_text_area = st.empty() # Placeholder for text results

with plot_col:
    st.subheader("Result Plot") # Changed header level
    plot_area = st.empty() # Placeholder for plot

# --- Calculation Logic ---
if calculate_button:
    if tonnes_consumed <= 0 or attained_lhv <= 0:
        st.error("Tonnes Consumed and LHV must be positive values.")
        # Clear previous results if inputs are invalid
        results_text_area.empty()
        plot_area.empty()
    else:
        # 1. Basic Calculations
        total_energy_mj_y = tonnes_consumed * attained_lhv
        attained_co2eq_t_y = total_energy_mj_y * attained_gfi / 1_000_000 # g to tonnes

        results = []
        # Using Markdown with bold for Calculation Basis header
        summary_text = f"**Calculation Basis:**\n"
        summary_text += f"Fuel: {fuel_type} ({tonnes_consumed:,.2f} t/y), Attained GFI: {attained_gfi:.2f} gCO₂eq/MJ\n"
        summary_text += f"LHV: {attained_lhv:,.1f} MJ/t\n"
        summary_text += f"Total Energy: {total_energy_mj_y:,.0f} MJ/y\n"
        summary_text += f"Reference GFI: {REFERENCE_GFI:.1f} gCO₂eq/MJ\n\n"

        summary_text += f"**Assumed SU trading price:** ${surplus_price:.2f}/t CO₂eq\n"
        summary_text += f"**RU Prices ($/t CO₂eq):**\n"
        summary_text += f"  2028-2030 (Fixed): T1=${T1_FIXED_PRICE:.2f}, T2=${T2_FIXED_PRICE:.2f}\n"
        summary_text += f"  2031 Onwards (User Input): T1=${t1_ru_price_user:.2f}, T2=${t2_ru_price_user:.2f}\n\n"

        summary_text += f"--- **Annual Results ({min(YEARS)}-{max(YEARS)})** ---\n\n"

        for year in YEARS:
            # (Calculation logic for targets, deficits, costs, surplus, revenue remains the same as previous correct version)
            # Get reduction percentages
            base_reduction_pct, direct_reduction_pct = TARGET_REDUCTIONS[year]

            # Calculate absolute GFI targets
            target_gfi_base = REFERENCE_GFI * (1 - base_reduction_pct / 100.0)
            target_gfi_direct = REFERENCE_GFI * (1 - direct_reduction_pct / 100.0)

            # Calculate target CO2 emissions in tonnes
            target_co2_base_t_y = total_energy_mj_y * target_gfi_base / 1_000_000
            target_co2_direct_t_y = total_energy_mj_y * target_gfi_direct / 1_000_000

            # Determine prices for the year
            t1_price = T1_FIXED_PRICE if year <= 2030 else t1_ru_price_user
            t2_price = T2_FIXED_PRICE if year <= 2030 else t2_ru_price_user

            # Initialize results for the year
            deficit_t1_co2 = 0.0
            deficit_t2_co2 = 0.0
            surplus_co2 = 0.0
            cost_t1 = 0.0
            cost_t2 = 0.0
            revenue_surplus = 0.0
            compliance_status = ""

            # --- Apply New Tiered Deficit/Surplus Logic ---
            if attained_co2eq_t_y > target_co2_direct_t_y:
                deficit_t1_co2 = attained_co2eq_t_y - target_co2_direct_t_y
                cost_t1 = deficit_t1_co2 * t1_price
                compliance_status = "Deficit vs Direct Target"
                if attained_co2eq_t_y > target_co2_base_t_y:
                    deficit_t2_co2 = attained_co2eq_t_y - target_co2_base_t_y
                    cost_t2 = deficit_t2_co2 * t2_price
                    compliance_status += " & Base Target"
                else:
                     compliance_status += " (Compliant vs Base)"
            else:
                surplus_co2 = target_co2_direct_t_y - attained_co2eq_t_y
                revenue_surplus = surplus_co2 * surplus_price
                compliance_status = "Surplus vs Direct Target"
                # This check might be redundant if Base Target GFI > Direct Target GFI always
                if attained_co2eq_t_y > target_co2_base_t_y:
                     compliance_status += " (Warning: Exceeds Base Target)"

            net_outcome = revenue_surplus - cost_t1 - cost_t2

            # --- Append Results Summary ---
            summary_text += f"--- **Year {year}** ---\n"
            # ... (rest of summary text generation is the same) ...
            summary_text += f"Targets GFI (Base / Direct): {target_gfi_base:.3f} ({base_reduction_pct:.1f}%) / {target_gfi_direct:.3f} ({direct_reduction_pct:.1f}%) gCO₂eq/MJ\n"
            summary_text += f"Target CO₂eq (Base / Direct): {target_co2_base_t_y:,.1f} t / {target_co2_direct_t_y:,.1f} t\n"
            summary_text += f"Attained CO₂eq: {attained_co2eq_t_y:,.1f} t\n"
            summary_text += f"Status: {compliance_status}\n"

            if net_outcome < 0: # Net Cost
                 summary_text += f"Deficits (T1 / T2): {deficit_t1_co2:,.3f} t / {deficit_t2_co2:,.3f} t CO₂eq\n"
                 summary_text += f"Net Outcome (Cost): ${abs(net_outcome):,.2f}\n"
                 if cost_t1 > 0:
                     summary_text += f"  (T1 RU Cost: ${cost_t1:,.2f} @ ${t1_price:.2f}/t)\n"
                 if cost_t2 > 0:
                     summary_text += f"  (T2 RU Cost: ${cost_t2:,.2f} @ ${t2_price:.2f}/t)\n"
            elif net_outcome > 0: # Net Revenue
                 summary_text += f"Surplus vs Direct: {surplus_co2:,.3f} t CO₂eq\n"
                 summary_text += f"Net Outcome (Potential Revenue): ${net_outcome:,.2f}\n"
                 summary_text += f"  (Potential SU Revenue: ${revenue_surplus:,.2f} @ ${surplus_price:.2f}/t)\n"
            else: # Zero balance
                 summary_text += f"Net Outcome: $0.00\n"
            summary_text += "\n"


            results.append({
                "Year": year,
                "Target GFI Base": target_gfi_base,
                "Target GFI Direct": target_gfi_direct,
                "Attained GFI": attained_gfi,
                "Target CO2 Base (t)": target_co2_base_t_y,
                "Target CO2 Direct (t)": target_co2_direct_t_y,
                "Attained CO2eq (t)": attained_co2eq_t_y,
                "Deficit T1 (t)": deficit_t1_co2,
                "Deficit T2 (t)": deficit_t2_co2,
                "Surplus (t)": surplus_co2,
                "Cost T1 ($)": cost_t1,
                "Cost T2 ($)": cost_t2,
                "Revenue Surplus ($)": revenue_surplus,
                "Net Outcome ($)": net_outcome,
                "T1 Price": t1_price,
                "T2 Price": t2_price,
                "Surplus Price": surplus_price
            })

        results_df = pd.DataFrame(results)

        # --- Display Calculation Results ---
        # Use markdown=True in text_area for bolding etc. if needed, but pure text is fine
        results_text_area.text_area(" ", summary_text, height=500, key="results_display")

        # --- Generate Plot ---
        # Convert outcomes to Millions USD for plotting
        results_df['Plot Revenue'] = results_df['Revenue Surplus ($)'].apply(lambda x: x / 1_000_000 if x > 0 else 0)
        results_df['Plot Cost T1'] = results_df['Cost T1 ($)'].apply(lambda x: -x / 1_000_000 if x > 0 else 0)
        results_df['Plot Cost T2'] = results_df['Cost T2 ($)'].apply(lambda x: -x / 1_000_000 if x > 0 else 0)

        # Create plot data
        plot_data = results_df[['Year']].copy()
        plot_data['Potential SU Revenue'] = results_df['Plot Revenue']
        plot_data['Tier 1 RU Cost'] = results_df['Plot Cost T1']
        plot_data['Tier 2 RU Cost'] = results_df['Plot Cost T2']

        # Melt data for Plotly express bar chart (long format)
        plot_data_melted = plot_data.melt(id_vars=['Year'],
                                          value_vars=['Potential SU Revenue', 'Tier 1 RU Cost', 'Tier 2 RU Cost'],
                                          var_name='Component',
                                          value_name='Value (Millions USD)')

        # Filter out zero values to avoid plotting them
        # Using a small tolerance might be safer than exact zero comparison with floats
        tolerance = 1e-9
        plot_data_melted = plot_data_melted[abs(plot_data_melted['Value (Millions USD)']) > tolerance]

        # ---- DEBUGGING: Optionally uncomment to see the data going into the plot ----
        # st.subheader("Debug: Plot Data (Melted & Filtered)")
        # st.dataframe(plot_data_melted)
        # ---- END DEBUGGING ----

        if plot_data_melted.empty:
            plot_area.warning("No significant cost or revenue data to plot.")
        else:
            # Define colors (ensure all potential keys are present)
            colors = {
                'Potential SU Revenue': 'lightblue', # Or a green color for revenue? e.g. '#2ca02c'
                'Tier 1 RU Cost': '#1f77b4',        # Blue
                'Tier 2 RU Cost': '#004c6d'         # Darker Blue
            }

            # Filter the color map to only include components present in the data
            components_present = plot_data_melted['Component'].unique()
            color_map_filtered = {k: v for k, v in colors.items() if k in components_present}


            try:
                fig = px.bar(plot_data_melted,
                             x='Year',
                             y='Value (Millions USD)',
                             color='Component',
                             title=f"Fuel: {fuel_type} ({tonnes_consumed:,.0f} t/y), Attained GFI: {attained_gfi:.2f} gCO₂eq/MJ",
                             labels={'Value (Millions USD)': 'Annual Revenue (+) / Cost (-) (Millions USD)'},
                             color_discrete_map=color_map_filtered, # Use filtered map
                             barmode='relative'
                            )

                # Customize layout
                fig.update_layout(
                    yaxis_title="Annual Revenue (+) / Cost (-) (Millions USD)",
                    xaxis_title="Year",
                    legend_title="Legend",
                    plot_bgcolor='white',
                    yaxis_gridcolor='lightgrey',
                    xaxis=dict(tickmode='linear'),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
                )
                fig.add_hline(y=0, line_width=1, line_color="black")

                # --- Display Plot ---
                plot_area.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                plot_area.error(f"An error occurred while generating the plot: {e}")
                st.exception(e) # Show full traceback in the app for debugging

# Initial display before calculation
else: # Use else block to ensure placeholders are shown only initially
     results_text_area.info("Enter parameters and click 'Calculate and Plot Results'.")
     plot_area.info("Plot will appear here after calculation.")


