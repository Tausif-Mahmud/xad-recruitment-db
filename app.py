import streamlit as st
import pandas as pd

# --- Configuration ---
st.set_page_config(page_title="Recruitment Dashboard", layout="centered")

# --- CSS Styling ---
st.markdown("""
    <style>
    /* 1. DYNAMIC BUTTON SIZING (Stack Overflow Approach)
       We target 'stColumn' divs that are NESTED inside other 'stColumn' divs.
       This ensures we affect the Button Grids (Level 2) but NOT the Main Page Layout (Level 1).
    */
    div[data-testid="stColumn"] div[data-testid="stColumn"] {
        width: fit-content !important;
        flex: unset !important;
        min-width: 0px !important;
    }
    
    div[data-testid="stColumn"] div[data-testid="stColumn"] * {
        width: fit-content !important;
    }

    /* 2. Button Styling */
    div.stButton > button {
        width: auto !important;
        height: auto !important;
        padding: 0.5rem 1rem !important;
        white-space: nowrap !important; /* Prevent text wrapping */
        word-break: keep-all !important;
    }

    /* 3. Active State Color Override (Pale Blue) */
    button[kind="primary"],
    button:active,
    button:focus,
    button:hover {
        background-color: #e6f3ff !important;
        color: #000000 !important;
        border-color: #2b7bba !important;
    }
    
    /* 4. Secondary Button Styling */
    button[kind="secondary"] {
        background-color: #f0f2f6;
        color: #31333F;
        border: 1px solid #d6d6d8;
    }
    
    /* Typography Overrides */
    h1 { font-size: 2.2rem !important; margin-bottom: 1rem !important; }
    h3 { font-size: 1.5rem !important; margin-top: 1.5rem !important; margin-bottom: 0.5rem !important; }
    .caption { font-size: 0.9rem; color: #666; margin-bottom: 10px; }
    
    </style>
""", unsafe_allow_html=True)

# --- Mappings ---
REGION_MAPPING = {
    "UAE": "United Arab Emirates",
    "KSA": "Kingdom of Saudi Arabia",
    "UK": "United Kingdom"
}

def get_region_name(acronym):
    return REGION_MAPPING.get(acronym, acronym)

# --- Session State ---
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'Home'
if 'selected_region' not in st.session_state:
    st.session_state.selected_region = None
if 'selected_staff' not in st.session_state:
    st.session_state.selected_staff = None

# Drill-down states
if 'reg_selected_project' not in st.session_state:
    st.session_state.reg_selected_project = None
if 'reg_selected_subdiv' not in st.session_state:
    st.session_state.reg_selected_subdiv = None
if 'staff_selected_subdiv_key' not in st.session_state:
    st.session_state.staff_selected_subdiv_key = None 

# --- Helper Functions ---

def reset_drill_down():
    st.session_state.reg_selected_project = None
    st.session_state.reg_selected_subdiv = None
    st.session_state.staff_selected_subdiv_key = None

def go_home():
    st.session_state.view_mode = 'Home'
    st.session_state.selected_region = None
    st.session_state.selected_staff = None
    reset_drill_down()

def go_to_region(region_name):
    if st.session_state.selected_region != region_name:
        reset_drill_down()
    st.session_state.view_mode = 'Region'
    st.session_state.selected_region = region_name
    st.session_state.selected_staff = None

def go_to_staff(staff_name):
    if st.session_state.selected_staff != staff_name:
        reset_drill_down()
    st.session_state.view_mode = 'Staff'
    st.session_state.selected_staff = staff_name
    st.session_state.selected_region = None

def sort_staff_list(staff_list):
    """Pins 'Manager Required' to top, sorts rest alphabetically."""
    unique_staff = sorted(list(set(staff_list)))
    if "Manager Required" in unique_staff:
        unique_staff.remove("Manager Required")
        return ["Manager Required"] + unique_staff
    return unique_staff

def format_staff_list(staff_list):
    if not len(staff_list): return ""
    staff_list = sort_staff_list(staff_list)
    if len(staff_list) == 1: return staff_list[0]
    return ", ".join(staff_list[:-1]) + " and " + staff_list[-1]

def is_global_simple_project(full_df, region, project_name):
    """
    Checks if a Project acts as its own Sub-Division in the master data.
    """
    subset = full_df[(full_df['Region'] == region) & (full_df['Project'] == project_name)]
    if subset.empty: return False
    unique_subs = subset['Sub_Division'].unique()
    return (len(unique_subs) == 1) and (unique_subs[0] == project_name)

# --- Dynamic Button Layout Engine ---
def render_dynamic_buttons(items, key_prefix, selected_val, on_click_action):
    """
    Renders buttons by calculating how many fit in a row based on text length.
    Uses st.columns() for each row, which combined with the CSS, creates tight wrapping.
    """
    if not items:
        return

    # Heuristic: Approximate max characters per row before wrapping
    # The CSS 'fit-content' will handle the actual width, but we need to group them logically.
    MAX_CHARS_PER_ROW = 80 
    
    rows = []
    current_row = []
    current_len = 0
    
    for item in items:
        # Estimate length: chars + padding buffer
        item_len = len(str(item)) + 6 
        
        if current_len + item_len > MAX_CHARS_PER_ROW and current_row:
            rows.append(current_row)
            current_row = []
            current_len = 0
        
        current_row.append(item)
        current_len += item_len
        
    if current_row:
        rows.append(current_row)

    # Render Rows
    for r_idx, row_items in enumerate(rows):
        # Create N columns for N items. 
        # The CSS ensures these columns shrink to fit the button width.
        cols = st.columns(len(row_items))
        
        for c_idx, item in enumerate(row_items):
            is_active = (selected_val == item)
            btn_type = "primary" if is_active else "secondary"
            
            # Use a callback lambda to handle click
            def click_handler(val=item):
                on_click_action(val)

            if cols[c_idx].button(item, key=f"{key_prefix}_{r_idx}_{c_idx}", type=btn_type):
                click_handler()

# --- Navigation Callbacks ---
def on_region_jump():
    val = st.session_state.nav_reg_jump
    if val and val != "Select...":
        go_to_region(val)
        st.session_state.nav_reg_jump = "Select..."

def on_staff_jump():
    val = st.session_state.nav_staff_jump
    if val and val != "Select...":
        go_to_staff(val)
        st.session_state.nav_staff_jump = "Select..."

# --- Data Loading ---
@st.cache_data
def load_data(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            try:
                df = pd.read_csv(uploaded_file)
            except UnicodeDecodeError:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, encoding='ISO-8859-1')
        else:
            df = pd.read_excel(uploaded_file)
        df.columns = [str(c).strip() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error parsing file: {e}")
        return pd.DataFrame()

# --- Sidebar ---
with st.sidebar:
    st.header("Upload Data")
    uploaded_file = st.file_uploader("Select File (CSV/XLSX)", type=['csv', 'xlsx'])
    
    st.markdown("---")
    st.header("Navigation")
    
    if st.button("🏠 Home / Reset"):
        go_home()
        st.rerun()

    if uploaded_file:
        df = load_data(uploaded_file)
        if not df.empty:
            st.header("Quick Jump")
            
            all_regions = sorted(df['Region'].dropna().unique())
            st.selectbox(
                "Go to Region:", 
                options=["Select..."] + list(all_regions),
                key="nav_reg_jump",
                on_change=on_region_jump
            )
            
            all_staff = sort_staff_list(df['Staff_Lead'].dropna().unique())
            st.selectbox(
                "Go to Staff:", 
                options=["Select..."] + list(all_staff),
                key="nav_staff_jump",
                on_change=on_staff_jump
            )

# --- Main Window ---

if uploaded_file is None:
    st.title("Company Recruitment Dashboard")
    st.info("👋 Please upload your Recruitment Data file (CSV or Excel) in the sidebar to begin.")
    st.stop()

if df.empty:
    st.warning("The uploaded file seems empty or could not be read.")
    st.stop()

# --- 1. HOME VIEW ---
if st.session_state.view_mode == 'Home':
    st.title("Company Recruitment Dashboard")
    
    # -- Region Section --
    st.subheader("Browse by Region")
    st.caption("See all current projects in a specific region.")
    
    all_regions = sorted(df['Region'].unique())
    
    # Map for logic: Display Name -> Code
    region_map = {get_region_name(r): r for r in all_regions}
    display_names = [get_region_name(r) for r in all_regions]
    
    def home_reg_click(display_name):
        code = region_map[display_name]
        go_to_region(code)
        st.rerun()
    
    # WRAPPER FIX: 
    # We wrap the buttons in a single column to trigger the "nested column" CSS rules.
    # This applies the 'width: fit-content' logic to the dynamic buttons inside.
    with st.columns(1)[0]:
        render_dynamic_buttons(display_names, "home_reg", None, home_reg_click)
            
    st.markdown("---")

    # -- Staff Section --
    st.subheader("Browse by Recruitment Staff")
    st.caption("See all sub-divisions managed by a specific staff member.")
    
    all_staff = sort_staff_list(df['Staff_Lead'].unique())
    
    def home_staff_click(s_name):
        go_to_staff(s_name)
        st.rerun()

    # WRAPPER FIX: Same as above, ensuring correct spacing/layout.
    with st.columns(1)[0]:
        render_dynamic_buttons(all_staff, "home_staff", None, home_staff_click)


# --- 2. REGION VIEW ---
elif st.session_state.view_mode == 'Region':
    region = st.session_state.selected_region
    full_region_name = get_region_name(region)
    st.title(f"Region: {full_region_name}")
    
    region_df = df[df['Region'] == region]

    # Level 1 Columns: Main Layout (3:1). 
    col_content, col_sidebar_list = st.columns([3, 1])

    # --- Right Side: Staff List ---
    with col_sidebar_list:
        st.subheader("Staff in this Region")
        st.caption("Recruitment staff active in this region.")
        staff_in_region = sort_staff_list(region_df['Staff_Lead'].unique())
        
        for s in staff_in_region:
            if st.button(s, key=f"reg_side_staff_{s}"):
                go_to_staff(s)
                st.rerun()

    # --- Left Side: Projects ---
    with col_content:
        st.subheader("Projects")
        st.caption("Select a project to view sub-divisions or positions.")
        
        projects = sorted(region_df['Project'].unique())
        
        def proj_click(p_name):
            if st.session_state.reg_selected_project == p_name:
                st.session_state.reg_selected_project = None
            else:
                st.session_state.reg_selected_project = p_name
            st.session_state.reg_selected_subdiv = None
            st.rerun()

        render_dynamic_buttons(projects, "reg_proj", st.session_state.reg_selected_project, proj_click)

        # -- Drill Down --
        if st.session_state.reg_selected_project:
            current_project = st.session_state.reg_selected_project
            proj_df = region_df[region_df['Project'] == current_project]
            is_simple = is_global_simple_project(df, region, current_project)
            
            if is_simple:
                st.markdown("---")
                st.subheader(f"Open Positions in {current_project}")
                
                staff_list = sorted(proj_df['Staff_Lead'].unique())
                staff_str = format_staff_list(staff_list)
                st.write(f"**Supervising Staff:** {staff_str}")
                
                roles = sorted(proj_df['Role'].unique())
                for role in roles:
                    st.markdown(f"- {role}")
            else:
                st.markdown("---")
                st.subheader(f"Sub-divisions for {current_project}")
                st.caption("Select a sub-division.")
                
                subdivs = sorted(proj_df['Sub_Division'].unique())
                
                def sub_click(sd_name):
                    if st.session_state.reg_selected_subdiv == sd_name:
                        st.session_state.reg_selected_subdiv = None
                    else:
                        st.session_state.reg_selected_subdiv = sd_name
                    st.rerun()

                render_dynamic_buttons(subdivs, "reg_sub", st.session_state.reg_selected_subdiv, sub_click)

                if st.session_state.reg_selected_subdiv:
                    current_subdiv = st.session_state.reg_selected_subdiv
                    details_df = proj_df[proj_df['Sub_Division'] == current_subdiv]
                    
                    st.markdown("---")
                    st.subheader(f"Open Positions in {current_subdiv}")
                    
                    staff_list = sorted(details_df['Staff_Lead'].unique())
                    staff_str = format_staff_list(staff_list)
                    st.write(f"**Supervising Staff:** {staff_str}")
                    
                    roles = sorted(details_df['Role'].unique())
                    for role in roles:
                        st.markdown(f"- {role}")


# --- 3. STAFF VIEW ---
elif st.session_state.view_mode == 'Staff':
    staff = st.session_state.selected_staff
    st.title(f"Recruitment Staff: {staff}")
    
    staff_df = df[df['Staff_Lead'] == staff]
    
    col_content, col_sidebar_list = st.columns([3, 1])

    # --- Right Side: Associated Regions ---
    with col_sidebar_list:
        st.subheader("Associated Regions")
        st.caption("Regions where this staff member is active.")
        associated_regions = sorted(staff_df['Region'].unique())
        
        for r in associated_regions:
            full_r = get_region_name(r)
            if st.button(full_r, key=f"staff_side_reg_{r}"):
                go_to_region(r)
                st.rerun()

    # --- Left Side: Managed Items ---
    with col_content:
        regions_active = sorted(staff_df['Region'].unique())
        
        for region_code in regions_active:
            full_reg_name = get_region_name(region_code)
            region_data = staff_df[staff_df['Region'] == region_code]
            
            staff_projects = sorted(region_data['Project'].unique())
            
            simple_projects = []
            complex_projects = {} 
            
            for proj in staff_projects:
                if is_global_simple_project(df, region_code, proj):
                    simple_projects.append(proj)
                else:
                    subs = sorted(region_data[region_data['Project'] == proj]['Sub_Division'].unique())
                    complex_projects[proj] = subs
            
            # 1. Simple Projects Group
            if simple_projects:
                st.subheader(f"Managed projects in {full_reg_name}")
                st.caption("Click to view open positions.")
                
                def simple_click(p_name):
                    key = f"{region_code}|{p_name}|{p_name}"
                    if st.session_state.staff_selected_subdiv_key == key:
                        st.session_state.staff_selected_subdiv_key = None
                    else:
                        st.session_state.staff_selected_subdiv_key = key
                    st.rerun()
                
                # Determine active based on complex key
                current_active_simple = None
                if st.session_state.staff_selected_subdiv_key:
                    parts = st.session_state.staff_selected_subdiv_key.split('|')
                    if len(parts) == 3 and parts[0] == region_code and parts[1] == parts[2]:
                        current_active_simple = parts[1]

                render_dynamic_buttons(simple_projects, f"staff_simple_{region_code}", current_active_simple, simple_click)

                # Show details
                if current_active_simple and current_active_simple in simple_projects:
                    st.markdown(f"**Open Positions in {current_active_simple}:**")
                    roles_df = region_data[(region_data['Project'] == current_active_simple) & (region_data['Sub_Division'] == current_active_simple)]
                    roles = sorted(roles_df['Role'].unique())
                    for role in roles:
                        st.markdown(f"- {role}")
                
                st.markdown("---")

            # 2. Complex Projects Groups
            for proj, subs in complex_projects.items():
                st.subheader(f"Managed sub-divisions in {proj} ({full_reg_name})")
                st.caption("Click a sub-division to view open positions.")
                
                def complex_click(sd_name):
                    key = f"{region_code}|{proj}|{sd_name}"
                    if st.session_state.staff_selected_subdiv_key == key:
                        st.session_state.staff_selected_subdiv_key = None
                    else:
                        st.session_state.staff_selected_subdiv_key = key
                    st.rerun()
                
                current_active_sub = None
                if st.session_state.staff_selected_subdiv_key:
                    parts = st.session_state.staff_selected_subdiv_key.split('|')
                    # Match Region and Project. 
                    if len(parts) == 3 and parts[0] == region_code and parts[1] == proj:
                        current_active_sub = parts[2]

                render_dynamic_buttons(subs, f"staff_complex_{region_code}_{proj}", current_active_sub, complex_click)
                
                # Show details if selected item is in this current group
                if current_active_sub and current_active_sub in subs:
                    st.markdown(f"**Open Positions in {current_active_sub}:**")
                    roles_df = region_data[(region_data['Project'] == proj) & (region_data['Sub_Division'] == current_active_sub)]
                    roles = sorted(roles_df['Role'].unique())
                    for role in roles:
                        st.markdown(f"- {role}")
                

                st.markdown("---")
