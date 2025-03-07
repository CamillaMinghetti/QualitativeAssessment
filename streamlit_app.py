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
    "*Colorectal cancer is one of the leading causes of death worldwide, "
    "and its early detection by colonoscopy is critical to improve the likelihood of success. "
    "However, two-dimensional visualization during colonoscopy can limit diagnostic accuracy, "
    "increasing the risk of undetected lesions. Depth estimation is therefore crucial to reconstruct a "
    "three-dimensional view of the bowel environment, improving diagnostic accuracy. "
    "However, obtaining accurate reference data (ground truth) in the clinical setting is particularly difficult "
    "due to the complexity of images and anatomical variability of patients. In this context, foundation AI models, "
    "pre-trained on huge amounts of data, could be a promising solution.*"
    "\n\n"
    "*To evaluate the effectiveness of AI models of depth estimation in endoscopy, it is crucial to involve clinicians directly, "
    "given the absence of an accurate ground truth with which to compare artificial intelligence predictions. "
    "For this reason, a questionnaire was developed for endoscopy specialists, with the aim of collecting opinions "
    "on the reliability of depth estimates generated by the analyzed models.*"
    "\n\n"
)
st.markdown(
    "**The questionnaire consists of viewing several videos. In the center, a real colonoscopy video will be displayed, "
    "while on the left and right, depth maps generated by two different AI models will be shown. \n\n"
    "The depth maps generated by the two predictive models use a color gradient, "
    "where blue represents the deepest areas, transitioning through green and yellow for intermediate depths, "
    "and finally red indicating the shallowest areas.**"
)

st.image("./frame_00379.png", caption="Example Depth Maps from AI Models", width=500)

# ----- Continue Button -----
if st.button("Continue"):
    # ----- Clinician Questions -----
    clinician = st.radio("Are you a clinician?", ["Yes", "No"])
    experience_level = None
    if clinician == "Yes":
        experience_level = st.radio("What is your experience level?", ["Resident", "Esperto"])
    
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
            sheet = client.open("Responses_qualitative_assessment").sheet1
            
            # Prepare row data (order should match your sheet header)
            row_data = [
                name,
                clinician,
                experience_level if clinician == "Yes" else "",
            ]
            row_data.extend([st.session_state["responses"][i] if st.session_state["responses"][i] else "No Response" for i in range(len(video_paths))])
            
            # Append row to the sheet
            sheet.append_row(row_data)
        except Exception as e:
            st.error(f"Error saving to Google Sheets: {e}")
        
        st.success("Your answers have been saved!")
        st.stop()

