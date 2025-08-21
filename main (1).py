import streamlit as st
from admin import show_admin_panel
from student import show_student_panel
import os

# ----- Page Configuration -----
st.set_page_config(page_title="Smart Attendance System", layout="centered")

# ----- Initialize Shared Session State -----
# These keys are primarily managed by the admin panel and loaded/saved via pickle.
# They are initialized here defensively, but their actual values are set by load_admin_state in admin.py.
for key in ["attendance_status", "attendance_codes", "attendance_limits"]:
    if key not in st.session_state:
        st.session_state[key] = {}

# ----- Ensure Refresh Trigger File Exists -----
# This file is used to signal updates between admin and student panels.
REFRESH_FILE = "refresh_trigger.txt"
if not os.path.exists(REFRESH_FILE):
    with open(REFRESH_FILE, "w") as f:
        f.write("init") # Write an initial value

# ----- App Title -----
st.title("📘 Smart Attendance System")

# ----- Tabs for Role-Based Panels -----
# This sets up the two main sections of your application.
tab1, tab2 = st.tabs(["🧑‍🏫 Admin Panel", "🎓 Student Panel"])

with tab1:
    show_admin_panel()

with tab2:
    show_student_panel()
