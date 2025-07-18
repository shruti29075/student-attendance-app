
import streamlit as st
import pandas as pd
import os
from datetime import datetime
import time
import pickle

# --- Constants ---
REFRESH_FILE = "refresh_trigger.txt"
STATE_FILE = "streamlit_session.pkl"

def load_admin_state():
    """Load admin state from pickle file."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "rb") as f:
                admin_state = pickle.load(f)
            return admin_state
        except Exception as e:
            st.error(f"Error loading portal state: {e}")
            return None
    else:
        st.error("Portal state file not found. Please contact admin.")
        return None

def get_class_list():
    """Return a list of all classroom CSVs (without .csv extension)."""
    return [f.replace(".csv", "") for f in os.listdir() if f.endswith(".csv")]

def auto_refresh_if_needed():
    """Check the refresh trigger file and rerun if changed."""
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = ""

    if os.path.exists(REFRESH_FILE):
        with open(REFRESH_FILE, "r") as f:
            current_value = f.read().strip()
        if current_value != st.session_state.last_refresh:
            st.session_state.last_refresh = current_value
            st.rerun()

def show_student_panel():
    st.title("📚 Student Attendance Portal")

    auto_refresh_if_needed()
    time.sleep(1) # Allow I/O sync to ensure admin updates are visible

    class_list = get_class_list()
    if not class_list:
        st.warning("No classrooms available. Please contact admin to create one.")
        return

    selected_class = st.selectbox("Select Your Class", class_list)

    st.subheader("📝 Mark Your Attendance")
    with st.form("attendance_form"):
        name = st.text_input("Full Name")
        roll = st.text_input("Roll Number")
        token = st.text_input("Attendance Token")

        submit = st.form_submit_button("Submit Attendance")

        if submit:
            if not name.strip() or not roll.strip() or not token.strip():
                st.warning("All fields are required.")
                return
            
            # --- NEW VALIDATION: Check if Roll Number is numeric ---
            if not roll.strip().isdigit():
                st.warning("Roll Number must be numeric.")
                return
            # --- END NEW VALIDATION ---

            admin_state = load_admin_state()
            if admin_state is None:
                return

            # Update session state with current admin settings
            st.session_state.attendance_status = admin_state.get("attendance_status", {})
            st.session_state.attendance_codes = admin_state.get("attendance_codes", {})
            st.session_state.attendance_limits = admin_state.get("attendance_limits", {})

            # Check if portal is open for selected class
            if not st.session_state.attendance_status.get(selected_class, False):
                st.error("❌ Attendance portal is currently CLOSED for this class.")
                return

            expected_token = st.session_state.attendance_codes.get(selected_class, "")
            if token != expected_token:
                st.error("❌ Invalid token.")
                return

            file_path = f"{selected_class}.csv"
            if not os.path.exists(file_path):
                st.error("❌ Classroom attendance file not found. Please contact admin to create it.")
                return

            current_date = datetime.now().strftime("%Y-%m-%d")

            try:
                df = pd.read_csv(file_path)
            except pd.errors.EmptyDataError:
                # Handle case where CSV is empty but exists (e.g., just headers)
                df = pd.DataFrame(columns=["Roll Number", "Name"])
            
            # Ensure 'Roll Number' and 'Name' are present as columns for merging/indexing
            if "Roll Number" not in df.columns or "Name" not in df.columns:
                 st.error("Attendance file format error: 'Roll Number' or 'Name' columns missing.")
                 return

            # Convert Roll Number to string for consistent matching
            df["Roll Number"] = df["Roll Number"].astype(str)

            # Ensure current_date column exists for limit check, initialize if not
            if current_date not in df.columns:
                df[current_date] = "" # Initialize new date column with empty strings

            # --- IMPORTANT: Reordered Logic for Duplicate and Limit Check ---

            # 1. Check for duplicate attendance for today
            student_row_index = df[df["Roll Number"] == roll].index
            
            already_marked = False
            if not student_row_index.empty:
                if df.loc[student_row_index[0], current_date] == 'P':
                    already_marked = True
            
            if already_marked:
                st.warning("⚠️ You have already marked your attendance for today.")
                return # Exit immediately if already marked

            # 2. Check token limit BEFORE marking attendance
            limit = st.session_state.attendance_limits.get(selected_class)
            if limit is not None:
                # Count current 'P' marks for today's column
                present_count_today = (df[current_date] == 'P').sum()
                
                # If adding this student would exceed the limit, prevent marking
                if present_count_today >= limit: # Use >= because this potential mark would make it +1
                    st.error("❌ Token limit reached. Attendance not recorded. Please contact your teacher.")
                    return # Exit immediately, do not mark attendance

            # --- If all checks pass, proceed to mark attendance ---
            if not student_row_index.empty:
                # Student exists and not already marked 'P' for today (checked above)
                df.loc[student_row_index[0], current_date] = 'P'
                st.success("✅ Attendance marked successfully!")
            else:
                # New student: Add new row and mark 'P' for today
                new_student_data = {"Roll Number": roll, "Name": name}
                
                # Fill new_student_data with empty strings for existing date columns
                for col in df.columns:
                    if col not in ["Roll Number", "Name"]:
                        new_student_data[col] = "" # Initialize existing date columns as absent

                new_student_data[current_date] = 'P' # Mark present for today
                
                # Append the new student row
                new_df_row = pd.DataFrame([new_student_data])
                df = pd.concat([df, new_df_row], ignore_index=True)
                st.success("✅ Attendance marked successfully!")

            # Sort by Roll Number (if numeric) for better readability
            try:
                df["Roll Number"] = df["Roll Number"].astype(int)
                df.sort_values(by="Roll Number", inplace=True)
                df["Roll Number"] = df["Roll Number"].astype(str) # keep consistency
            except ValueError:
                # If roll numbers are not purely numeric, sort as string
                df.sort_values(by="Roll Number", inplace=True)

            df.to_csv(file_path, index=False)
            st.rerun() # Rerun to clear form and update display if any.
