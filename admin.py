import streamlit as st
import os
import pandas as pd
from datetime import datetime
import pickle

# ---- Admin credentials ----
# Read credentials from st.secrets (from .streamlit/secrets.toml or Streamlit Cloud secrets)

ADMIN_USERNAME = st.secrets["ADMIN_USERNAME"]
ADMIN_PASSWORD = st.secrets["ADMIN_PASSWORD"]

STATE_FILE = "streamlit_session.pkl"

# ---- Helper Functions ----

def save_admin_state():
    admin_state = {
        "attendance_status": st.session_state.attendance_status,
        "attendance_codes": st.session_state.attendance_codes,
        "attendance_limits": st.session_state.attendance_limits
    }
    with open(STATE_FILE, "wb") as f:
        pickle.dump(admin_state, f)

def load_admin_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "rb") as f:
                admin_state = pickle.load(f)
            return admin_state
        except Exception as e:
            st.error(f"Error loading admin state: {e}")
            # If there's an error loading, return empty dicts to avoid crashing
            return {
                "attendance_status": {},
                "attendance_codes": {},
                "attendance_limits": {}
            }
    else:
        # Return empty dicts if no saved state
        return {
            "attendance_status": {},
            "attendance_codes": {},
            "attendance_limits": {}
        }

def get_class_list():
    """Return a list of all classroom CSVs (without .csv extension)."""
    # Filter only .csv files and remove the extension
    files = [f.replace(".csv", "") for f in os.listdir() if f.endswith(".csv") and f != STATE_FILE.replace(".pkl", ".csv")]
    return files

def create_classroom(class_name):
    """Create a new classroom CSV file with headers if it doesn't exist."""
    file_path = f"{class_name}.csv"
    if not os.path.exists(file_path):
        # Initialize with Roll Number and Name only. Date columns will be added dynamically.
        df = pd.DataFrame(columns=["Roll Number", "Name"])
        df.to_csv(file_path, index=False)

def delete_classroom(class_name):
    """Delete a classroom CSV file."""
    file_path = f"{class_name}.csv"
    if os.path.exists(file_path):
        os.remove(file_path)
        # Also remove relevant entries from session state
        if class_name in st.session_state.attendance_status:
            del st.session_state.attendance_status[class_name]
        if class_name in st.session_state.attendance_codes:
            del st.session_state.attendance_codes[class_name]
        if class_name in st.session_state.attendance_limits:
            del st.session_state.attendance_limits[class_name]
        save_admin_state() # Save updated state after deletion

def trigger_student_refresh():
    """Update the refresh trigger file to notify students to reload their session."""
    with open("refresh_trigger.txt", "w") as f:
        f.write(datetime.now().isoformat())

def show_admin_panel():
    st.title("Admin Panel")

    # --- Login Form ---
    if "admin_logged_in" not in st.session_state:
        st.session_state.admin_logged_in = False

    if not st.session_state.admin_logged_in:
        st.subheader("Admin Login")
        username = st.text_input("Username", key="admin_username_input")
        password = st.text_input("Password", type="password", key="admin_password_input")
        if st.button("Login", key="admin_login_button"):
            if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                
                # Load saved state on successful login
                admin_state = load_admin_state()
                st.session_state.attendance_status = admin_state.get("attendance_status", {})
                st.session_state.attendance_codes = admin_state.get("attendance_codes", {})
                st.session_state.attendance_limits = admin_state.get("attendance_limits", {})

                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid credentials")
        return # Stop execution here if not logged in

    # --- Logout Button (Only visible if logged in) ---
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout Admin"):
        st.session_state.admin_logged_in = False
        st.info("Logged out successfully.")
        st.rerun()

    # --- Initialize Session Variables if not present ---
    # These should already be loaded from save_admin_state on login, but defensive check
    if "attendance_status" not in st.session_state:
        st.session_state.attendance_status = {}
    if "attendance_codes" not in st.session_state:
        st.session_state.attendance_codes = {}
    if "attendance_limits" not in st.session_state:
        st.session_state.attendance_limits = {}

    # --- Classroom Management ---
    st.subheader("Manage Classrooms")

    col1, col2 = st.columns([2, 1])
    with col1:
        new_class = st.text_input("Add New Classroom (e.g., class_10A)", key="new_class_input")
    with col2:
        # Consolidated button rendering and logic
        if st.button("Add Classroom", key="add_class_button_unified"): # Only one call to st.button
            if not new_class.strip():
                st.warning("Classroom name cannot be empty.")
            elif new_class.strip() in get_class_list():
                st.warning(f"Classroom '{new_class}' already exists.")
            else:
                create_classroom(new_class.strip())
                st.success(f"Classroom '{new_class}' created.")
                st.rerun()

    class_list = get_class_list()
    if not class_list:
        st.warning("No classrooms found. Please add a classroom.")
        # If no classes, stop further processing that relies on a selected class
        return

    selected_class = st.selectbox("Select Classroom", class_list, key="selected_class_dropdown")

    if st.button("Delete Selected Classroom", key="delete_class_button"):
        delete_classroom(selected_class)
        st.warning(f"Classroom '{selected_class}' deleted.")
        st.rerun()

    st.markdown("---")

    # --- Attendance Control ---
    st.subheader(f"Attendance Control for '{selected_class}'")

    current_status = st.session_state.attendance_status.get(selected_class, False)
    status_text = "OPEN" if current_status else "CLOSED"
    st.info(f"Current Attendance Status: **{status_text}**")

    col_open, col_close = st.columns(2)
    with col_open:
        if st.button("Open Attendance", key="open_attendance_button"):
            st.session_state.attendance_status[selected_class] = True
            save_admin_state()
            trigger_student_refresh()
            st.success(f"Attendance portal for {selected_class} is OPEN.")
            st.rerun() # Rerun to update status text immediately

    with col_close:
        if st.button("Close Attendance", key="close_attendance_button"):
            st.session_state.attendance_status[selected_class] = False
            save_admin_state()
            trigger_student_refresh()
            st.info(f"Attendance portal for {selected_class} is CLOSED.")
            st.rerun() # Rerun to update status text immediately

    # Display current code and limit
    current_code = st.session_state.attendance_codes.get(selected_class, "")
    current_limit = st.session_state.attendance_limits.get(selected_class, 1) # Default to 1 if not set

    st.markdown(f"**Current Code:** `{current_code}`")
    st.markdown(f"**Current Limit:** `{current_limit}`")

    # Set token/code and token limit
    code = st.text_input("Set New Attendance Code", value=current_code, key=f"code_{selected_class}")
    limit = st.number_input("Set Token Limit (e.g., max students allowed)", min_value=1, value=current_limit, step=1, key=f"limit_{selected_class}")

    if st.button("Update Code & Limit", key="update_code_limit_button"):
        st.session_state.attendance_codes[selected_class] = code
        st.session_state.attendance_limits[selected_class] = int(limit) # Ensure integer
        save_admin_state()
        st.success(f"Code and token limit updated for {selected_class}")
        st.rerun() # Rerun to update displayed current code/limit

    st.markdown("---")

    # --- View Attendance ---
    st.subheader(f"Attendance for {selected_class}")
    
    file_path = f"{selected_class}.csv"
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                st.info(f"No attendance recorded yet for {selected_class}.")
            else:
                st.dataframe(df)

                st.download_button(
                    "Download Attendance CSV",
                    df.to_csv(index=False).encode('utf-8'), # Ensure utf-8 encoding for download
                    file_name=f"attendance_{selected_class}_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    key="download_csv_button"
                )
        except pd.errors.EmptyDataError:
            st.info(f"Classroom '{selected_class}' CSV is empty. No attendance recorded yet.")
        except Exception as e:
            st.error(f"Error reading attendance data: {e}")
    else:
        st.warning(f"No attendance file found for {selected_class}. Please create the classroom first.")
