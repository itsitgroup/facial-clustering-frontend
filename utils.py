import os
import json
import base64
import io
import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw


# Helper functions
def load_json(json_file):
    """Load the JSON content from the uploaded file and remove cluster -4."""
    data = json.load(json_file)
    filtered_data = [cluster for cluster in data if cluster.get("cluster_label") != -4]
    return filtered_data


def decode_base64_image(base64_string):
    """Decode base64 string to an image."""
    if not base64_string or not isinstance(base64_string, str):
        return None
    try:
        image_data = base64.b64decode(base64_string)
        return Image.open(io.BytesIO(image_data))
    except Exception:
        st.warning("Failed to decode thumbnail: Invalid Base64 format")
        return None


def process_faces_by_image(faces):
    """Group faces by file_name and combine bounding boxes."""
    image_data = {}  # file_name -> {"cords": [], "face_ids": [], "has_multiple_faces": False}

    for face in faces:
        file_name = face.get("file_name")
        if not file_name:
            st.warning("A face entry is missing 'file_name'. Skipping this face.")
            continue

        cords = face["cords"]
        face_id = face["face_id"]
        if file_name not in image_data:
            image_data[file_name] = {
                "cords": [cords],
                "face_ids": [face_id],
                "has_multiple_faces": False,
            }
        else:
            image_data[file_name]["cords"].append(cords)
            image_data[file_name]["face_ids"].append(face_id)
            image_data[file_name]["has_multiple_faces"] = True  # Mark as multi-face

    return image_data


def draw_bounding_boxes_with_colors(image_dir, image_data):
    """Draw bounding boxes with unique colors for each face."""
    image_dir = image_dir.strip("'\"")
    if not os.path.isdir(image_dir):
        st.error(f"The directory '{image_dir}' does not exist. Please check the path.")
        return []

    color_palette = ["red", "green", "blue", "orange", "purple", "cyan", "yellow", "pink", "lime", "brown"]

    images = []
    image_dir_files = {f.lower(): f for f in os.listdir(image_dir)}  # Case-insensitive matching

    for file_name, data in image_data.items():
        actual_file_name = image_dir_files.get(file_name.lower())

        if not actual_file_name:
            st.warning(f"File {file_name} not found in {image_dir}. Skipping...")
            continue

        image_path = os.path.join(image_dir, actual_file_name)
        try:
            image = Image.open(image_path).convert("RGB")
            draw = ImageDraw.Draw(image)

            clickable_regions = []
            for idx, cords in enumerate(data["cords"]):
                color = color_palette[idx % len(color_palette)]
                draw.rectangle(cords, outline=color, width=5)  # Use unique color for each bounding box
                face_id = data["face_ids"][idx]
                clickable_regions.append((face_id, cords, color))  # Include color in clickable regions

            images.append((file_name, image, clickable_regions))
        except Exception as e:
            st.error(f"Error processing file {file_name}: {e}")
    return images


# def toggle_checkbox(key):
#     """Toggle the state of a checkbox."""
#     st.session_state[key] = not st.session_state[key]


@st.dialog("Face Details")
def show_face_details(face_info):
    """Display a modal with face details."""
    st.markdown("## Face Details")

    # Prepare data for display, ensuring all values are strings
    data = {
        "Attribute": [
            "Cluster Label", "Cluster Size", "Face ID", "File Name", 
            "Coordinates", "Width", "Height", "Alignment Method", 
            "Score", "Blur Score"
        ],
        "Value": [
            str(face_info.get("cluster_label", "N/A")),
            str(face_info.get("cluster_size", "N/A")),
            str(face_info.get("face_id", "N/A")),
            str(face_info.get("file_name", "N/A")),
            str(face_info.get("cords", "N/A")),
            str(face_info.get("width", "N/A")),
            str(face_info.get("height", "N/A")),
            str(face_info.get("alignment_method", "N/A")),
            str(face_info.get("score", "N/A")),
            str(face_info.get("blur_score", "N/A")),
        ]
    }

    # Convert data to a DataFrame for display
    df = pd.DataFrame(data)

    # Display the table
    st.table(df)
    st.button("Close")