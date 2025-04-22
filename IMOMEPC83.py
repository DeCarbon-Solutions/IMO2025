import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import datetime

# --- Configuration & Data ---

# Predefined Fuel Data (LHV in MJ/t, GFI in gCO2eq/MJ)
PREDEFINED_FUELS = {
    "HFO": {"LHV": 40200, "GFI": 93.30},
    "LNG": {"LHV": 48000, "GFI": 68.00},
    "B24": {"LHV": 41500, "GFI": 75.00},
    "Bio-Diesel(B100)": {"LHV": 37200, "GFI": 31.00},
    "e-Diesel":{"LHV": 44000, "GFI": 37.00},
    "e-Ammonia": {"LHV": 18600, "GFI": 3.00},
    "bio-Methanol": {"LHV": 19900, "GFI": 5.00},
}
# Ensure HFO is always an option, list others for selection
BENCHMARK_FUEL = "HFO"
COMPARISON_FUEL_OPTIONS = [f for f in PREDEFINED_FUELS if f != BENCHMARK_FUEL]

# Reference GFI Value
REFERENCE_GFI = 93.3 # gCO2eq/MJ

# Reduction Targets (%) relative to Reference GFI
TARGET_REDUCTIONS = {
    # Year: (Base Target Reduction %, Direct Compliance Target Reduction %)
    2028: (4.0, 17.0), 2029: (6.0, 19.0), 2030: (8.0, 21.0),
    2031: (12.4, 25.4), 2032: (16.8, 29.8), 2033: (21.2, 34.2),
    2034: (25.6, 38.6), 2035: (30.0, 43.0),
}
YEARS = list(TARGET_REDUCTIONS.keys())

# RU Prices ($/t CO2eq)
T1_FIXED_PRICE = 100.0 # Price for Tier 1 deficit
T2_FIXED_PRICE = 380.0 # Price for Tier 2 deficit (Fixed period)

# --- Helper Functions ---

def calculate_compliance_costs(fuel_name, fuel_data, tonnes_consumed, pricing):
    """Calculates compliance costs/revenue and generates detailed summary text."""
    if not fuel_data or tonnes_consumed <= 0 or fuel_data["LHV"] <= 0:
        return pd.DataFrame(), ""

    attained_lhv = fuel_data["LHV"]
    attained_gfi = fuel_data["GFI"]
    total_energy_mj_y = tonnes_consumed * attained_lhv
    attained_co2eq_t_y = total_energy_mj_y * attained_gfi / 1_000_000

    results_list = []
    # Initial part of summary text (will be prepended before loop)
    summary_header = f"**Calculation Basis ({fuel_name}):**\n"
    summary_header += f"Fuel: {fuel_name} ({tonnes_consumed:,.2f} t/y), Attained GFI: {attained_gfi:.2f} gCO₂eq/MJ\n"
    summary_header += f"LHV: {attained_lhv:,.1f} MJ/t\n"
    summary_header += f"Total Energy: {total_energy_mj_y:,.0f} MJ/y\n"
    summary_header += f"Reference GFI: {REFERENCE_GFI:.1f} gCO₂eq/MJ\n\n"
    summary_header += f"**Pricing Assumptions:**\n"
    summary_header += f"  SU Trading Price: ${pricing['surplus']:.2f}/t CO₂eq\n"
    summary_header += f"  RU Prices (2028-30): T1=${T1_FIXED_PRICE:.2f}, T2=${T2_FIXED_PRICE:.2f}\n"
    summary_header += f"  RU Prices (2031+): T1=${pricing['t1_user']:.2f}, T2=${pricing['t2_user']:.2f}\n\n"
    summary_header += f"--- **Annual Calculation Results** ---\n\n"

    annual_summary_parts = [] # Store text parts for each year

    for year in YEARS:
        year_text = "" # Text for this specific year
        base_reduction_pct, direct_reduction_pct = TARGET_REDUCTIONS[year]
        target_gfi_base = REFERENCE_GFI * (1 - base_reduction_pct / 100.0)
        target_gfi_direct = REFERENCE_GFI * (1 - direct_reduction_pct / 100.0)
        target_co2_base_t_y = total_energy_mj_y * target_gfi_base / 1_000_000
        target_co2_direct_t_y = total_energy_mj_y * target_gfi_direct / 1_000_000

        t1_price = T1_FIXED_PRICE if year <= 2030 else pricing['t1_user']
        t2_price = T2_FIXED_PRICE if year <= 2030 else pricing['t2_user']
        surplus_unit_price = pricing['surplus']

        deficit_t1_co2, deficit_t2_co2, surplus_co2 = 0.0, 0.0, 0.0
        cost_t1, cost_t2, revenue_surplus = 0.0, 0.0, 0.0
        compliance_status = ""

        # --- Compliance Logic ---
        if attained_co2eq_t_y > target_co2_direct_t_y:
            deficit_t1_co2 = attained_co2eq_t_y - target_co2_direct_t_y
            cost_t1 = deficit_t1_co2 * t1_price
            compliance_status = "Deficit vs Direct Target"
            if attained_co2eq_t_y > target_co2_base_t_y:
                deficit_t2_co2 = attained_co2eq_t_y - target_co2_base_t_y
                cost_t2 = deficit_t2_co2 * t2_price
                compliance_status += " & Base Target"
            # No "else" needed here for status, base compliance is implied if inner if is false
        else:
            surplus_co2 = target_co2_direct_t_y - attained_co2eq_t_y
            revenue_surplus = surplus_co2 * surplus_unit_price
            compliance_status = "Surplus vs Direct Target"
            # Optional check, might be impossible if Base Target GFI > Direct Target GFI
            if attained_co2eq_t_y > target_co2_base_t_y:
                 compliance_status += " (Warning: Exceeds Base Target)"

        net_outcome = revenue_surplus - cost_t1 - cost_t2

        # --- Build Year Text (matching the detailed format) ---
        year_text += f"--- **Year {year}** ---\n"
        year_text += f"Targets GFI (Base / Direct): {target_gfi_base:.3f} ({base_reduction_pct:.1f}%) / {target_gfi_direct:.3f} ({direct_reduction_pct:.1f}%) gCO₂eq/MJ\n"
        year_text += f"Target CO₂eq (Base / Direct): {target_co2_base_t_y:,.1f} t / {target_co2_direct_t_y:,.1f} t\n"
        year_text += f"Attained CO₂eq: {attained_co2eq_t_y:,.1f} t\n"
        year_text += f"Status: {compliance_status}\n"

        if net_outcome < 0: # Net Cost
             if deficit_t1_co2 > 0: year_text += f"Tier 1 Deficit: {deficit_t1_co2:,.3f} t CO₂eq\n"
             if deficit_t2_co2 > 0: year_text += f"Tier 2 Deficit: {deficit_t2_co2:,.3f} t CO₂eq\n"
             year_text += f"Net Outcome (Cost): ${abs(net_outcome):,.2f}\n"
             if cost_t1 > 0: year_text += f"  (T1 RU Cost: ${cost_t1:,.2f} @ ${t1_price:.2f}/t)\n"
             if cost_t2 > 0: year_text += f"  (T2 RU Cost: ${cost_t2:,.2f} @ ${t2_price:.2f}/t)\n"
        elif net_outcome > 0: # Net Revenue
             year_text += f"Surplus vs Direct: {surplus_co2:,.3f} t CO₂eq\n"
             year_text += f"Net Outcome (Potential Revenue): ${net_outcome:,.2f}\n"
             year_text += f"  (Potential SU Revenue: ${revenue_surplus:,.2f} @ ${surplus_unit_price:.2f}/t)\n"
        else: # Zero balance
             year_text += f"Net Outcome: $0.00\n"
        year_text += "\n"
        annual_summary_parts.append(year_text)

        # --- Store data for DataFrame ---
        results_list.append({
            "Year": year, "Fuel": fuel_name,
            "Net Outcome ($)": net_outcome,
            "Revenue Surplus ($)": revenue_surplus,
            "Cost T1 ($)": cost_t1, "Cost T2 ($)": cost_t2,
            "Status": compliance_status,
        })

    results_df = pd.DataFrame(results_list)
    # Add Million $ columns
    results_df['Net Outcome (Millions USD)'] = results_df['Net Outcome ($)'] / 1_000_000
    results_df['Revenue Surplus (Millions USD)'] = results_df['Revenue Surplus ($)'] / 1_000_000
    results_df['Cost T1 (Millions USD)'] = results_df['Cost T1 ($)'] / 1_000_000
    results_df['Cost T2 (Millions USD)'] = results_df['Cost T2 ($)'] / 1_000_000

    # Combine header and annual parts for the full detailed text
    full_summary_text = summary_header + "".join(annual_summary_parts)

    return results_df, full_summary_text

def plot_comparison(df_combined, tonnes_consumed):
    """Generates the comparison plot for multiple fuels."""
    if df_combined.empty: return go.Figure()
    fig = px.bar(df_combined, x='Year', y='Net Outcome (Millions USD)', color='Fuel',
                 title=f"Comparison of Net Annual Outcome ({tonnes_consumed:,.0f} t/y Consumed)",
                 labels={'Net Outcome (Millions USD)': 'Net Revenue (+) / Cost (-) (Millions USD)'},
                 barmode='group', color_discrete_sequence=px.colors.qualitative.Plotly)
    fig.update_layout(yaxis_title="Net Revenue (+) / Cost (-) (Millions USD)", xaxis_title="Year",
                      legend_title="Fuel Type", plot_bgcolor='white', yaxis_gridcolor='lightgrey',
                      xaxis=dict(tickmode='linear'),
                      legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5))
    fig.add_hline(y=0, line_width=1, line_color="black")
    return fig

# --- Initialize Session State ---
# We still need session state to store inputs and results across reruns
if 'selected_comparison_fuels' not in st.session_state:
    st.session_state.selected_comparison_fuels = [] # User selection (excluding HFO initially)
if 'final_fuel_list' not in st.session_state:
     st.session_state.final_fuel_list = [BENCHMARK_FUEL] # Always start with HFO
if 'tonnes_consumed' not in st.session_state:
    st.session_state.tonnes_consumed = 5000.0
if 'pricing' not in st.session_state:
    st.session_state.pricing = {'surplus': 380.0, 't1_user': 100.0, 't2_user': 380.0}
if 'comparison_results_df' not in st.session_state:
    st.session_state.comparison_results_df = pd.DataFrame()
if 'detailed_summaries' not in st.session_state: # Dict to store {fuel_name: summary_text}
    st.session_state.detailed_summaries = {}
if 'show_results' not in st.session_state:
    st.session_state.show_results = False

# --- Callback to reset results on input change ---
def reset_calculation():
    st.session_state.show_results = False
    st.session_state.comparison_results_df = pd.DataFrame()
    st.session_state.detailed_summaries = {}
    # Update final fuel list based on current selection when inputs change
    update_final_fuel_list()

def update_final_fuel_list():
     # Start with HFO, add selected unique fuels
    user_selection = st.session_state.get('compare_fuels_multi', []) # Get current multiselect value
    st.session_state.final_fuel_list = [BENCHMARK_FUEL] + [f for f in user_selection if f != BENCHMARK_FUEL]


# --- App Layout ---

st.set_page_config(layout="wide")

st.markdown("<h1 style='text-align: center; color: #004c6d;'>ABS EAL: IMO MEPC 83 - Fuel Compliance Comparison</h1>", unsafe_allow_html=True)
st.markdown("<h2 style='text-align: center; color: grey;'>Cost and Compliance Calculator </h2>", unsafe_allow_html=True)

# --- Input Section (All visible) ---

# Step 1 (Implied): Select Fuels for Comparison
st.subheader("1. Select Additional Fuels for Comparison")
st.markdown(f"**{BENCHMARK_FUEL}** is always included as the benchmark.")
st.session_state.selected_comparison_fuels = st.multiselect(
    f"Select fuels to compare against {BENCHMARK_FUEL}:",
    COMPARISON_FUEL_OPTIONS, # Offer fuels other than HFO
    default=st.session_state.selected_comparison_fuels, # Remember previous selection
    key='compare_fuels_multi', # Unique key for multiselect
    on_change=reset_calculation # Reset results if selection changes
)
# Update the final list immediately for display/calculation prep
update_final_fuel_list()
if len(st.session_state.final_fuel_list) > 1: # Show info if comparing > 1 fuel
    selected_info = " | ".join([f"{f} (GFI: {PREDEFINED_FUELS[f]['GFI']:.2f})" for f in st.session_state.final_fuel_list])
    st.info(f"Comparing: {selected_info}")
else:
    st.info(f"Only comparing the benchmark: {BENCHMARK_FUEL} (GFI: {PREDEFINED_FUELS[BENCHMARK_FUEL]['GFI']:.2f})")

st.divider()

# Step 2 (Implied): Enter Consumption
st.subheader("2. Enter Annual Fuel Consumption")
col_cons1, col_cons2 = st.columns([1, 2])
with col_cons1:
    st.session_state.tonnes_consumed = st.number_input(
        "Tonnes Consumed per annum (applied to all fuels):",
        min_value=0.0, value=st.session_state.tonnes_consumed, step=100.0, format="%.2f",
        key='tonnes_consumed_input',
        on_change=reset_calculation # Reset if consumption changes
    )
st.divider()

# Step 3 (Implied): Review Pricing
st.subheader("3. Review Pricing Assumptions")
col_price1, col_price2 = st.columns(2)
with col_price1:
    st.session_state.pricing['surplus'] = st.number_input(
        "Assumed surplus unit (SU) trading price ($/t CO₂eq):",
        min_value=0.0, value=st.session_state.pricing['surplus'], step=10.0, format="%.1f",
        key='surplus_price_input', on_change=reset_calculation
        )
    st.session_state.pricing['t1_user'] = st.number_input(
        "Tier 1 RU Price (2031+) ($/t CO₂eq):",
        min_value=0.0, value=st.session_state.pricing['t1_user'], step=10.0, format="%.1f",
        key='t1_price_input', on_change=reset_calculation
        )
with col_price2:
    st.session_state.pricing['t2_user'] = st.number_input(
        "Tier 2 RU Price (2031+) ($/t CO₂eq):",
        min_value=0.0, value=st.session_state.pricing['t2_user'], step=10.0, format="%.1f",
        key='t2_price_input', on_change=reset_calculation
        )
    st.caption(f"Note: Fixed prices apply 2028-2030 (T1=${T1_FIXED_PRICE:.2f}, T2=${T2_FIXED_PRICE:.2f})")
st.divider()

# Step 4 (Implied): Calculate
st.subheader("4. Calculate Comparison")

# --- Highlighted Calculation Button ---
st.markdown("""
<style>
.stButton>button {
    background-color: #FF4B4B; color: white; font-weight: bold;
    padding: 10px 20px; border: none; border-radius: 5px; font-size: 1.1em;
}
.stButton>button:hover { background-color: #E03C3C; color: white; }
</style>
""", unsafe_allow_html=True)

if st.button("Calculate and Show Results"):
    if not st.session_state.final_fuel_list:
        st.error("Please select at least one fuel to compare.")
    elif st.session_state.tonnes_consumed <= 0:
        st.error("Tonnes Consumed must be positive.")
        reset_calculation() # Clear any potentially old results
    else:
        st.session_state.show_results = True
        all_results_list = []
        calculated_summaries = {}

        with st.spinner("Calculating..."):
            for fuel_name in st.session_state.final_fuel_list:
                fuel_data = PREDEFINED_FUELS.get(fuel_name)
                if fuel_data:
                    df, summary_txt = calculate_compliance_costs(
                        fuel_name, fuel_data,
                        st.session_state.tonnes_consumed,
                        st.session_state.pricing
                    )
                    if not df.empty:
                        all_results_list.append(df)
                        calculated_summaries[fuel_name] = summary_txt
                else:
                    st.warning(f"Could not find data for fuel: {fuel_name}")

            if all_results_list:
                st.session_state.comparison_results_df = pd.concat(all_results_list, ignore_index=True)
                st.session_state.detailed_summaries = calculated_summaries
            else:
                st.session_state.comparison_results_df = pd.DataFrame()
                st.session_state.detailed_summaries = {}
                st.error("No valid results could be calculated.")

st.divider()

# --- Results Section ---
if st.session_state.show_results:
    st.header("Calculation Results")

    if not st.session_state.comparison_results_df.empty:
        # 1. Comparison Plot
        st.subheader("Comparison Plot (Net Outcome)")
        fig_comp = plot_comparison(st.session_state.comparison_results_df, st.session_state.tonnes_consumed)
        if not fig_comp.data:
             st.info("No comparison data to plot.")
        else:
            st.plotly_chart(fig_comp, use_container_width=True)
        st.divider()

        # 2. Summary Table
        st.subheader("Comparison Summary Table")
        try:
            summary_table = st.session_state.comparison_results_df.groupby('Fuel')['Net Outcome (Millions USD)'].agg(['mean', 'sum']).reset_index()
            summary_table.rename(columns={'mean': 'Avg Annual Net Outcome (M USD)', 'sum': 'Total Net Outcome 2028-35 (M USD)'}, inplace=True)
            # Sort table to potentially match multiselect order or keep HFO first if desired
            summary_table['Fuel'] = pd.Categorical(summary_table['Fuel'], categories=st.session_state.final_fuel_list, ordered=True)
            summary_table = summary_table.sort_values('Fuel')
            st.dataframe(summary_table.style.format({
                'Avg Annual Net Outcome (M USD)': '{:,.2f}',
                'Total Net Outcome 2028-35 (M USD)': '{:,.2f}'
                }), use_container_width=True)
        except Exception as e:
            st.error(f"Could not generate summary table: {e}")
        st.divider()

        # 3. Detailed Year-by-Year Results per Fuel
        st.subheader("Detailed Annual Results by Fuel")
        if not st.session_state.detailed_summaries:
             st.warning("Detailed summaries are not available.")
        else:
            for fuel_name in st.session_state.final_fuel_list: # Iterate in the final calculated order
                summary_text = st.session_state.detailed_summaries.get(fuel_name)
                if summary_text:
                    with st.expander(f"Show Detailed Annual Results for: {fuel_name}"):
                        st.text_area(f"Details for {fuel_name}", summary_text, height=500, key=f"details_{fuel_name}", disabled=True)
                else:
                    st.warning(f"Detailed summary for {fuel_name} could not be retrieved.")

    else:
         st.warning("No results to display. Click 'Calculate and Show Results' after selecting fuels and entering consumption.")

# Add a footer
st.divider() # Add a line above the footer for separation
current_year = datetime.datetime.now().year
# Add your copyright line using st.caption
st.caption(f"© {current_year} [Developed by ABS EAL Lead: Dr. Chenxi Ji]. All rights reserved.")
# Keep the original disclaimer caption as well
st.caption("Calculator based on specified IMO MEPC 83 rules and MEPC 391(80) assumptions. Always verify results with latest official IMO regulations.")

