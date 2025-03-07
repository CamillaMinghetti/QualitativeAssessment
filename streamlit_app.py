import streamlit as st
import pandas as pd
import os
import json
import datetime
import re
import base64
import streamlit.components.v1 as components

# Google Sheets libraries
import gspread
from google.oauth2.service_account import Credentials

# Set page layout to wide for responsiveness
st.set_page_config(layout="wide")

# ----- Helper Function for Video Display -----
def get_video_html(video_path, max_width):
    try:
        with open(video_path, "rb") as f:
            video_bytes = f.read()
        encoded_video = base64.b64encode(video_bytes).decode()
    except Exception as e:
        st.error(f"Error loading video: {e}")
        return ""
    # Use inline CSS to ensure responsiveness: full width (up to max_width pixels)
    video_html = f"""
    <style>
      .responsive-video {{
        width: 100%;
        max-width: {max_width}px;
        height: auto;
      }}
    </style>
    <video class="responsive-video" controls>
      <source src="data:video/mp4;base64,{encoded_video}" type="video/mp4">
      Your browser does not support the video tag.
    </video>
    """
    return video_html

# ----- App Title and Description -----
st.title("Qualitative Performance Assessment of EndoDAC and Depth Pro Models")
st.write(
    "The video in the center shows a colonoscopy, while the two side videos (left and right) "
    "represent depth maps generated by two predictive models, where blue indicates deeper areas "
    "and red indicates shallower areas. \n"
    "Which of the two side videos (left or right) do you think best reflects reality in terms of accuracy in depth estimation?"
)

# ----- Clinician Questions -----
clinician = st.radio("Are you a clinician?", ["Yes", "No"])
experience_level = None
procedures_performed = None
if clinician == "Yes":
    experience_level = st.radio("What is your experience level?", ["Specializzando", "Resident", "Esperto"])
    procedures_performed = st.radio(
        "How many endoscopic procedures have you performed?",
        ["<50", "Between 50 and 100", ">100"]
    )

# ----- Name Input -----
name = st.text_input("Please enter your name")

# ----- Video Display Settings -----
VIDEO_MAX_WIDTH = 640  # Maximum width in pixels; video will scale responsively

# ----- Video Paths -----
video_paths = [
    "./VideoColonoscopy3.mp4",
    "./VideoColonoscopy4.mp4",
    "./VideoColonoscopy5.mp4",
    "./VideoColonoscopy6.mp4",
    "./VideoColonoscopy7.mp4",
    "./VideoColonoscopy8.mp4",
    "./VideoColonoscopy9.mp4",
    "./VideoColonoscopy10.mp4",
    "./VideoColonoscopy11.mp4",
    "./VideoColonoscopy12.mp4",
]

# ----- Session State Initialization -----
if "question_index" not in st.session_state:
    st.session_state["question_index"] = 0
if "responses" not in st.session_state:
    # Initialize responses with None
    st.session_state["responses"] = [None] * len(video_paths)

# ----- Questionnaire and Video Display -----
if name:
    st.header("Questionnaire")
    question_index = st.session_state["question_index"]
    st.subheader(f"Question {question_index + 1}")
    
    # Display video using HTML embed with responsive CSS
    video_path = video_paths[question_index]
    video_html = get_video_html(video_path, VIDEO_MAX_WIDTH)
    if video_html:
        # The height is approximate; adjust as needed for your videos
        components.html(video_html, height=int(VIDEO_MAX_WIDTH * 0.75))
    
    # Define options with a placeholder as the first option
    options = ["Select an option", "Left", "Right"]
    existing_response = st.session_state["responses"][question_index]
    if existing_response in ["Left", "Right"]:
        default_index = options.index(existing_response)
    else:
        default_index = 0  # Placeholder
    
    response = st.radio(
        "Which of the two side videos (left or right) do you think best reflects reality in terms of accuracy in depth estimation?", 
        options, 
        key=f"question_{question_index}",
        index=default_index
    )
    
    # Store the response only if it's a valid selection
    if response in ["Left", "Right"]:
        st.session_state["responses"][question_index] = response
    else:
        st.session_state["responses"][question_index] = None
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Previous") and question_index > 0:
            st.session_state["question_index"] -= 1
            st.rerun()
    with col2:
        # Disable Next if no valid answer has been made
        if st.button("Next", disabled=(st.session_state["responses"][question_index] is None)) and question_index < len(video_paths) - 1:
            st.session_state["question_index"] += 1
            st.rerun()
    
    # ----- Submission Block -----
    if question_index == len(video_paths) - 1 and st.button("Submit Answers", disabled=(st.session_state["responses"][question_index] is None)):
        # Create a folder for JSON responses if it does not exist
        responses_folder = "responses"
        if not os.path.exists(responses_folder):
            os.makedirs(responses_folder)
        
        # Sanitize name for filename
        safe_name = re.sub(r'[^\w\-_. ]', '_', name).strip()
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"{safe_name}_{timestamp}.json"
        file_path = os.path.join(responses_folder, file_name)
        
        # Prepare response data
        new_data = {
            "Name": name,
            "Clinician": clinician,
            "Experience Level": experience_level if clinician == "Yes" else None,
            "Procedures Performed": procedures_performed if clinician == "Yes" else None,
        }
        for i in range(len(video_paths)):
            new_data[f"Question {i+1}"] = st.session_state["responses"][i] if st.session_state["responses"][i] else "No Response"
        
        # Save locally as JSON
        try:
            with open(file_path, "w") as f:
                json.dump(new_data, f, indent=4)
        except Exception as e:
            st.error(f"Error saving JSON file: {e}")
        
        # ----- Google Sheets Setup -----
        try:
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds_data = st.secrets["gcp_service_account"]
            creds = Credentials.from_service_account_info(creds_data, scopes=scope)
            client = gspread.authorize(creds)
            # Open your Google Sheet (ensure the sheet is shared with your service account)
            sheet = client.open("Quantitative_assesment").sheet1
            
            # Prepare row data (order should match your sheet header)
            row_data = [
                name,
                clinician,
                experience_level if clinician == "Yes" else "",
                procedures_performed if clinician == "Yes" else ""
            ]
            row_data.extend([st.session_state["responses"][i] if st.session_state["responses"][i] else "No Response" for i in range(len(video_paths))])
            
            # Append row to the sheet
            sheet.append_row(row_data)
        except Exception as e:
            st.error(f"Error saving to Google Sheets: {e}")
        
        st.success("Your answers have been saved!")
        st.stop()

