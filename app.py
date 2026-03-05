"""
XAD Recruitment Details Dashboard
===================================
A Streamlit web application that displays open recruitment positions
sourced from a Google Sheet. Provides three navigable views:

  1. Home — Browse by Region or by Recruitment Staff.
  2. Region — Drill down from Region → Project → Sub-division → Roles.
  3. Staff — View all projects/sub-divisions managed by a specific staff member, grouped by region.

Data is pulled live via CSV export from Google Sheets and cached by
Streamlit. The sidebar provides Home, Refresh, and Quick Jump controls.

Projects are classified as 'simple' (no sub-divisions; Sub_Division == Project)
or 'complex' (multiple sub-divisions), which determines whether the drill-down
shows a sub-division selection step or goes directly to open positions.

Requires: GitHub repository to host the script. Deployed via Streamlit Community Cloud service.
"""

import streamlit as st
import pandas as pd

# ── Configuration ──────────────────────────────────────────────────────────
st.set_page_config(page_title="XAD Recruitment Details", layout="wide")

# Google Sheet CSV export URL
# To produce this URL: copy the Google Sheet URL and change "edit?" to "export?format=csv&"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1HDXLPqdZh3FlK_dmLzi-TzgPMNh9CLk_eMJjLK5g-uY/export?format=csv&gid=249760352"

# ── CSS Styling ────────────────────────────────────────────────────────────
st.markdown("""
    <style>
    /* 1. Dynamic Button Sizing */
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
    
    /* Hide GitHub Fork Option and Icon*/
    .stAppToolbar {
        display: none;
    }

    </style>
""", unsafe_allow_html=True)

# ── Region Acronym Mappings ────────────────────────────────────────────────
REGION_MAPPING = {
    "UAE": "United Arab Emirates",
    "KSA": "Kingdom of Saudi Arabia",
    "UK": "United Kingdom",
    "Unspecified Region": "Unspecified Region"
}

def get_region_name(acronym):
    """Return the full region name for a given acronym, or the acronym itself if unmapped."""
    return REGION_MAPPING.get(acronym, acronym)

# ── Session State Initialisation ───────────────────────────────────────────
# Current view and selection state
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'Home'
if 'selected_region' not in st.session_state:
    st.session_state.selected_region = None
if 'selected_staff' not in st.session_state:
    st.session_state.selected_staff = None

# Drill-down states for Region and Staff views
if 'reg_selected_project' not in st.session_state:
    st.session_state.reg_selected_project = None
if 'reg_selected_subdiv' not in st.session_state:
    st.session_state.reg_selected_subdiv = None
if 'staff_selected_subdiv_key' not in st.session_state:
    st.session_state.staff_selected_subdiv_key = None 

# ── Navigation Helpers ─────────────────────────────────────────────────────

def reset_drill_down():
    """Clear all drill-down selections (project, sub-division) across views."""
    st.session_state.reg_selected_project = None
    st.session_state.reg_selected_subdiv = None
    st.session_state.staff_selected_subdiv_key = None

def go_home():
    """Navigate to the Home view and reset all selections."""
    st.session_state.view_mode = 'Home'
    st.session_state.selected_region = None
    st.session_state.selected_staff = None
    reset_drill_down()

def go_to_region(region_name):
    """Navigate to the Region view for the given region acronym."""
    if st.session_state.selected_region != region_name:
        reset_drill_down()
    st.session_state.view_mode = 'Region'
    st.session_state.selected_region = region_name
    st.session_state.selected_staff = None

def go_to_staff(staff_name):
    """Navigate to the Staff view for the given staff member."""
    if st.session_state.selected_staff != staff_name:
        reset_drill_down()
    st.session_state.view_mode = 'Staff'
    st.session_state.selected_staff = staff_name
    st.session_state.selected_region = None

# ── Sorting Helpers ────────────────────────────────────────────────────────

def sort_staff_list(staff_list):
    """Sort staff names alphabetically, pinning 'Manager Required' to top
    and 'Unspecified' to bottom."""
    unique_staff = sorted(list(set(staff_list)))
    
    special_top = []
    if "Manager Required" in unique_staff:
        unique_staff.remove("Manager Required")
        special_top.append("Manager Required")
        
    special_bottom = []
    if "Unspecified" in unique_staff:
        unique_staff.remove("Unspecified")
        special_bottom.append("Unspecified")
        
    return special_top + unique_staff + special_bottom

def sort_region_list(region_list):
    """Sort regions alphabetically, pinning 'Unspecified Region' to bottom."""
    unique = sorted(list(set(region_list)))
    if "Unspecified Region" in unique:
        unique.remove("Unspecified Region")
        unique.append("Unspecified Region")
    return unique

def sort_general_list(item_list):
    """Sort items alphabetically, pinning 'Unspecified' to bottom."""
    unique = sorted(list(set(item_list)))
    if "Unspecified" in unique:
        unique.remove("Unspecified")
        unique.append("Unspecified")
    return unique

# ── Display Helpers ────────────────────────────────────────────────────────

def format_staff_for_display(staff_list):
    """Format a staff list into a readable string for the 'Supervising Staff' line.

    Removes 'Manager Required' from the display list (tracked separately).
    Returns (formatted_string, is_manager_required).
    """
    clean_list = sorted(list(set(staff_list)))
    is_mgr_req = False
    
    if "Manager Required" in clean_list:
        clean_list.remove("Manager Required")
        is_mgr_req = True
        
    if not clean_list:
        return "None", is_mgr_req
        
    if len(clean_list) == 1:
        return clean_list[0], is_mgr_req
        
    return ", ".join(clean_list[:-1]) + " and " + clean_list[-1], is_mgr_req

def is_global_simple_project(full_df, region, project_name):
    """Return True if a project has no real sub-divisions (Sub_Division == Project name).

    A 'simple' project skips the sub-division selection step in the drill-down
    and goes directly to listing open positions.
    """
    subset = full_df[(full_df['Region'] == region) & (full_df['Project'] == project_name)]
    if subset.empty: return False
    unique_subs = subset['Sub_Division'].unique()
    return (len(unique_subs) == 1) and (unique_subs[0] == project_name)

# ── Dynamic Button Layout Engine ──────────────────────────────────────────

def render_dynamic_buttons(items, key_prefix, selected_val, on_click_action):
    """Render a row-wrapped set of buttons that auto-wrap based on text length.

    Buttons are grouped into rows using a character-length heuristic
    (MAX_CHARS_PER_ROW). The currently selected item is rendered as a
    'primary' button; all others are 'secondary'.

    Args:
        items:           List of button labels to render.
        key_prefix:      Unique prefix for Streamlit widget keys.
        selected_val:    Currently active item (highlighted as primary), or None.
        on_click_action: Callback function invoked with the clicked item's label.
    """
    if not items: return

    MAX_CHARS_PER_ROW = 80 
    
    rows = []
    current_row = []
    current_len = 0
    
    for item in items:
        item_len = len(str(item)) + 6  # Character length + padding buffer
        
        if current_len + item_len > MAX_CHARS_PER_ROW and current_row:
            rows.append(current_row)
            current_row = []
            current_len = 0
        
        current_row.append(item)
        current_len += item_len
        
    if current_row:
        rows.append(current_row)

    for r_idx, row_items in enumerate(rows):
        cols = st.columns(len(row_items))
        
        for c_idx, item in enumerate(row_items):
            is_active = (selected_val == item)
            btn_type = "primary" if is_active else "secondary"
            
            if cols[c_idx].button(item, key=f"{key_prefix}_{r_idx}_{c_idx}", type=btn_type):
                on_click_action(item)

# ── Sidebar Navigation Callbacks ──────────────────────────────────────────

def on_region_jump():
    """Handle the Quick Jump region selectbox change."""
    val = st.session_state.nav_reg_jump
    if val and val != "Select...":
        go_to_region(val)
        st.session_state.nav_reg_jump = "Select..."

def on_staff_jump():
    """Handle the Quick Jump staff selectbox change."""
    val = st.session_state.nav_staff_jump
    if val and val != "Select...":
        go_to_staff(val)
        st.session_state.nav_staff_jump = "Select..."

# ── Data Loading & Cleaning ───────────────────────────────────────────────

@st.cache_data
def load_data():
    """Fetch recruitment data from Google Sheets and clean it for display.

    Cleaning rules:
      - Empty Region → 'Unspecified Region'
      - Empty Staff_Lead → 'Unspecified'
      - Empty Role → 'Unspecified'
      - If both Project and Sub_Division are empty → both become 'Unspecified'
      - If only Sub_Division is empty → Sub_Division inherits Project value
      - If only Project is empty → Project inherits Sub_Division value

    Returns a cleaned DataFrame, or None on fetch failure.
    """
    try:
        df = pd.read_csv(SHEET_URL, dtype=str)
        
        df.columns = [str(c).strip() for c in df.columns]
        
        # 1. Handle Regions
        df['Region'] = df['Region'].fillna("Unspecified Region")
        df.loc[df['Region'].str.strip() == '', 'Region'] = "Unspecified Region"
        
        # 2. Handle Staff
        df['Staff_Lead'] = df['Staff_Lead'].fillna("Unspecified")
        df.loc[df['Staff_Lead'].str.strip() == '', 'Staff_Lead'] = "Unspecified"
        
        # 3. Handle Role
        df['Role'] = df['Role'].fillna("Unspecified")
        df.loc[df['Role'].str.strip() == '', 'Role'] = "Unspecified"
        
        # 4. Handle Project & Sub-Division inheritance logic
        df['Project'] = df['Project'].fillna("")
        df['Sub_Division'] = df['Sub_Division'].fillna("")
        
        mask_both_empty = (df['Project'] == "") & (df['Sub_Division'] == "")
        df.loc[mask_both_empty, 'Project'] = "Unspecified"
        df.loc[mask_both_empty, 'Sub_Division'] = "Unspecified"
        
        mask_proj_ok_sub_empty = (df['Project'] != "") & (df['Sub_Division'] == "")
        df.loc[mask_proj_ok_sub_empty, 'Sub_Division'] = df.loc[mask_proj_ok_sub_empty, 'Project']
        
        mask_sub_ok_proj_empty = (df['Sub_Division'] != "") & (df['Project'] == "")
        df.loc[mask_sub_ok_proj_empty, 'Project'] = df.loc[mask_sub_ok_proj_empty, 'Sub_Division']
        
        for col in df.columns:
            df[col] = df[col].astype(str).str.strip()

        return df
    except Exception as e:
        return None

# ── Pre-Calculation & Data Loading ─────────────────────────────────────────
df = load_data()

all_regions = []
all_staff = []

if df is not None and not df.empty:
    all_regions = sort_region_list(df['Region'].unique())
    all_staff = sort_staff_list(df['Staff_Lead'].unique())

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Main Menu")
    
    if st.button("🏠 Home", use_container_width=True):
        go_home()
        st.rerun()

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")

    df = load_data()

    if df is not None and not df.empty:
        st.header("Quick Jump")
        
        st.selectbox(
            "Go to Region:", 
            options=["Select..."] + list(all_regions),
            key="nav_reg_jump",
            on_change=on_region_jump
        )
        
        st.selectbox(
            "Go to Staff:", 
            options=["Select..."] + list(all_staff),
            key="nav_staff_jump",
            on_change=on_staff_jump
        )

# ══════════════════════════════════════════════════════════════════════════════
# MAIN WINDOW
# ══════════════════════════════════════════════════════════════════════════════

if df is None:
    st.title("XAD Recruitment Details")
    st.error("⚠️ Error loading data from Google Sheets.")
    st.markdown("""
        **Possible causes:**
        * The Google Sheet URL is incorrect or the sheet has been deleted.
        * The Sheet permissions are not set to 'Anyone with the link' (Viewer).
        * The 'gid' (Sheet ID) in the URL is incorrect.
        
        Please check the source spreadsheet and try clicking **Refresh Data** in the sidebar.
    """)
    st.stop()

if df.empty:
    st.title("XAD Recruitment Details")
    st.warning("⚠️ The Google Sheet appears to be empty. Please check the data source.")
    st.stop()


# ── 1. HOME VIEW ──────────────────────────────────────────────────────────
if st.session_state.view_mode == 'Home':
    st.title("XAD Recruitment Details")
    
    # Region buttons
    st.subheader("Browse by Region")
    st.caption("See all current projects in a specific region.")
    
    region_map = {get_region_name(r): r for r in all_regions}
    display_names = [get_region_name(r) for r in all_regions]
    
    def home_reg_click(display_name):
        code = region_map[display_name]
        go_to_region(code)
        st.rerun()
    
    with st.columns(1)[0]:
        render_dynamic_buttons(display_names, "home_reg", None, home_reg_click)
            
    st.markdown("---")

    # Staff buttons
    st.subheader("Browse by Recruitment Staff")
    st.caption("See all sub-divisions managed by a specific staff member.")
    
    def home_staff_click(s_name):
        go_to_staff(s_name)
        st.rerun()

    with st.columns(1)[0]:
        render_dynamic_buttons(all_staff, "home_staff", None, home_staff_click)


# ── 2. REGION VIEW ────────────────────────────────────────────────────────
elif st.session_state.view_mode == 'Region':
    region = st.session_state.selected_region
    full_region_name = get_region_name(region)
    st.title(f"Region: {full_region_name}")
    
    region_df = df[df['Region'] == region]

    col_content, col_sidebar_list = st.columns([3, 1])

    # Right sidebar: Staff list for this region
    with col_sidebar_list:
        st.subheader("Staff in this Region")
        st.caption("Recruitment staff active in this region.")
        staff_in_region = sort_staff_list(region_df['Staff_Lead'].unique())
        
        for s in staff_in_region:
            if st.button(s, key=f"reg_side_staff_{s}"):
                go_to_staff(s)
                st.rerun()

    # Left content: Project drill-down
    with col_content:
        st.subheader("Projects")
        st.caption("Select a project to view sub-divisions or positions.")
        
        projects = sort_general_list(region_df['Project'].unique())
        
        def proj_click(p_name):
            if st.session_state.reg_selected_project == p_name:
                st.session_state.reg_selected_project = None
            else:
                st.session_state.reg_selected_project = p_name
            st.session_state.reg_selected_subdiv = None
            st.rerun()

        render_dynamic_buttons(projects, "reg_proj", st.session_state.reg_selected_project, proj_click)

        # Drill-down: Project → Sub-division → Roles
        if st.session_state.reg_selected_project:
            current_project = st.session_state.reg_selected_project
            proj_df = region_df[region_df['Project'] == current_project]
            is_simple = is_global_simple_project(df, region, current_project)
            
            if is_simple:
                # Simple project: show roles directly (no sub-division step)
                st.markdown("---")
                st.subheader(f"Open Positions in {current_project}")
                
                staff_list = proj_df['Staff_Lead'].unique()
                staff_str, is_mgr_req = format_staff_for_display(staff_list)
                
                st.write(f"**Supervising Staff:** {staff_str}")
                if is_mgr_req:
                    st.markdown(f"**⚠️ Manager required for {current_project} project.**")
                
                roles = sorted(proj_df['Role'].unique())
                for role in roles:
                    st.markdown(f"- {role}")
            else:
                # Complex project: show sub-division selection first
                st.markdown("---")
                st.subheader(f"Sub-divisions for {current_project}")
                st.caption("Select a sub-division.")
                
                subdivs = sort_general_list(proj_df['Sub_Division'].unique())
                
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
                    
                    staff_list = details_df['Staff_Lead'].unique()
                    staff_str, is_mgr_req = format_staff_for_display(staff_list)
                    
                    st.write(f"**Supervising Staff:** {staff_str}")
                    if is_mgr_req:
                        st.markdown(f"**⚠️ Manager required for {current_subdiv} sub-division.**")
                    
                    roles = sorted(details_df['Role'].unique())
                    for role in roles:
                        st.markdown(f"- {role}")


# ── 3. STAFF VIEW ─────────────────────────────────────────────────────────
elif st.session_state.view_mode == 'Staff':
    staff = st.session_state.selected_staff
    
    # Custom header text for the 'Manager Required' pseudo-staff entry
    if staff == "Manager Required":
        st.title("Vacant Management Positions")
        header_context_project = "Projects in" 
        header_context_sub = "Sub-divisions in"
        caption_text = "Managers are required for the following sub-divisions."
    else:
        st.title(f"Recruitment Staff: {staff}")
        header_context_project = "Managed projects in"
        header_context_sub = "Managed sub-divisions in"
        caption_text = "Click to view open positions."
    
    staff_df = df[df['Staff_Lead'] == staff]
    
    col_content, col_sidebar_list = st.columns([3, 1])

    # Right sidebar: Associated regions
    with col_sidebar_list:
        st.subheader("Associated Regions")
        st.caption("Regions where this staff member is active.")
        associated_regions = sort_region_list(staff_df['Region'].unique())
        
        for r in associated_regions:
            full_r = get_region_name(r)
            if st.button(full_r, key=f"staff_side_reg_{r}"):
                go_to_region(r)
                st.rerun()

    # Left content: Projects and sub-divisions grouped by region
    with col_content:
        regions_active = sort_region_list(staff_df['Region'].unique())
        
        for region_code in regions_active:
            full_reg_name = get_region_name(region_code)
            region_data = staff_df[staff_df['Region'] == region_code]
            
            staff_projects = sort_general_list(region_data['Project'].unique())
            
            # Classify projects as simple (no sub-divisions) or complex
            simple_projects = []
            complex_projects = {} 
            
            for proj in staff_projects:
                if is_global_simple_project(df, region_code, proj):
                    simple_projects.append(proj)
                else:
                    subs = sort_general_list(region_data[region_data['Project'] == proj]['Sub_Division'].unique())
                    complex_projects[proj] = subs
            
            # Simple projects: show as a flat button group
            if simple_projects:
                st.subheader(f"{header_context_project} {full_reg_name}")
                st.caption(caption_text)
                
                def simple_click(p_name):
                    key = f"{region_code}|{p_name}|{p_name}"
                    if st.session_state.staff_selected_subdiv_key == key:
                        st.session_state.staff_selected_subdiv_key = None
                    else:
                        st.session_state.staff_selected_subdiv_key = key
                    st.rerun()
                
                # Decode the composite key to find the active simple project
                current_active_simple = None
                if st.session_state.staff_selected_subdiv_key:
                    parts = st.session_state.staff_selected_subdiv_key.split('|')
                    if len(parts) == 3 and parts[0] == region_code and parts[1] == parts[2]:
                        current_active_simple = parts[1]

                render_dynamic_buttons(simple_projects, f"staff_simple_{region_code}", current_active_simple, simple_click)

                if current_active_simple and current_active_simple in simple_projects:
                    st.markdown(f"**Open Positions in {current_active_simple}:**")
                    roles_df = region_data[(region_data['Project'] == current_active_simple) & (region_data['Sub_Division'] == current_active_simple)]
                    roles = sorted(roles_df['Role'].unique())
                    for role in roles:
                        st.markdown(f"- {role}")
                
                st.markdown("---")

            # Complex projects: show sub-division buttons per project
            for proj, subs in complex_projects.items():
                st.subheader(f"{header_context_sub} {proj} ({full_reg_name})")
                st.caption(caption_text)
                
                def complex_click(sd_name):
                    key = f"{region_code}|{proj}|{sd_name}"
                    if st.session_state.staff_selected_subdiv_key == key:
                        st.session_state.staff_selected_subdiv_key = None
                    else:
                        st.session_state.staff_selected_subdiv_key = key
                    st.rerun()
                
                # Decode the composite key to find the active sub-division
                current_active_sub = None
                if st.session_state.staff_selected_subdiv_key:
                    parts = st.session_state.staff_selected_subdiv_key.split('|')
                    if len(parts) == 3 and parts[0] == region_code and parts[1] == proj:
                        current_active_sub = parts[2]

                render_dynamic_buttons(subs, f"staff_complex_{region_code}_{proj}", current_active_sub, complex_click)
                
                if current_active_sub and current_active_sub in subs:
                    st.markdown(f"**Open Positions in {current_active_sub}:**")
                    roles_df = region_data[(region_data['Project'] == proj) & (region_data['Sub_Division'] == current_active_sub)]
                    roles = sorted(roles_df['Role'].unique())
                    for role in roles:
                        st.markdown(f"- {role}")
                
                st.markdown("---")
