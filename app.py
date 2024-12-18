import os
import json
import base64
import io
import streamlit as st
from PIL import Image, ImageDraw

# Set wide page layout
st.set_page_config(page_title="Cluster Visualization App", layout="wide")


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
    image_data = {}  # file_name -> {"cords": [], "has_multiple_faces": False}

    for face in faces:
        file_name = face.get("file_name")
        if not file_name:
            st.warning("A face entry is missing 'file_name'. Skipping this face.")
            continue

        cords = face["cords"]
        if file_name not in image_data:
            image_data[file_name] = {"cords": [cords], "has_multiple_faces": False}
        else:
            image_data[file_name]["cords"].append(cords)
            image_data[file_name]["has_multiple_faces"] = True  # Mark as multi-face

    return image_data


def draw_bounding_boxes(image_dir, image_data):
    """Draw bounding boxes on images grouped by file_name."""
    image_dir = image_dir.strip("'\"")
    if not os.path.isdir(image_dir):
        st.error(f"The directory '{image_dir}' does not exist. Please check the path.")
        return []

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

            for cords in data["cords"]:
                draw.rectangle(cords, outline="red", width=5)

            images.append((file_name, image))
        except Exception as e:
            st.error(f"Error processing file {file_name}: {e}")
    return images


# Callback for checkbox toggle
def toggle_checkbox():
    """Toggle the state of the 'Show Images with Multiple Faces Only' checkbox."""
    st.session_state.show_multiple_faces_only = not st.session_state.show_multiple_faces_only


# Streamlit app
st.title("Cluster Visualization App")

# Initialize session state for selected cluster and checkbox
if "selected_cluster_label" not in st.session_state:
    st.session_state.selected_cluster_label = None
if "show_multiple_faces_only" not in st.session_state:
    st.session_state.show_multiple_faces_only = False

# File uploader for JSON
uploaded_file = st.file_uploader("Upload JSON File", type=["json"])
image_dir = st.text_input("Enter the path to the image directory")

if uploaded_file and image_dir:
    # Load JSON while filtering out cluster -4
    clusters = load_json(uploaded_file)

    # Sidebar for cluster selection
    st.sidebar.title("Clusters")
    st.sidebar.subheader("Select a Cluster")

    for cluster in clusters:
        cluster_label = cluster["cluster_label"]
        cluster_size = cluster["cluster_size"]

        # Process faces to check for multi-face images
        image_data = process_faces_by_image(cluster["faces"])
        num_images_with_multiple_faces = sum(1 for data in image_data.values() if data["has_multiple_faces"])

        # Display cluster label and size
        st.sidebar.markdown(f"### Cluster {cluster_label} (Size: {cluster_size})")

        # Display warning if there are images with multiple faces
        if num_images_with_multiple_faces > 0:
            st.sidebar.markdown(
                f"<span style='color:red;'>⚠️ Multiple Faces in {num_images_with_multiple_faces} image(s)</span>",
                unsafe_allow_html=True
            )

        # Display thumbnails for each cluster
        cols = st.sidebar.columns(3)  # Display thumbnails in 3 columns
        for i in range(1, 4):
            thumbnail_key = f"thumbnail_{i}"
            if thumbnail_key in cluster:
                thumbnail = decode_base64_image(cluster[thumbnail_key])
                if thumbnail:
                    with cols[i - 1]:
                        st.image(thumbnail, use_container_width=True)

        # Add a button to select this cluster
        if st.sidebar.button(f"Select Cluster {cluster_label}", key=f"select_{cluster_label}"):
            st.session_state.selected_cluster_label = cluster_label

    # Default to the first cluster if none selected
    if st.session_state.selected_cluster_label is None:
        st.session_state.selected_cluster_label = clusters[0]["cluster_label"]

    # Extract selected cluster data
    selected_cluster_label = st.session_state.selected_cluster_label
    selected_data = next(c for c in clusters if c["cluster_label"] == selected_cluster_label)
    cluster_size = selected_data["cluster_size"]

    # Process faces and group by file_name
    image_data = process_faces_by_image(selected_data["faces"])

    # Checkbox to filter images with multiple faces
    st.checkbox(
        "Show Images with Multiple Faces Only",
        value=st.session_state.show_multiple_faces_only,
        key="checkbox",
        on_change=toggle_checkbox,
    )

    # Filter images if checkbox is checked
    filtered_data = {
        file_name: data for file_name, data in image_data.items()
        if not st.session_state.show_multiple_faces_only or data["has_multiple_faces"]
    }

    # Main area: Display Cluster Label and Size
    st.header(f"Cluster {selected_cluster_label} (Size: {cluster_size})")
    if st.session_state.show_multiple_faces_only and not filtered_data:
        st.info("No images with multiple faces in this cluster.")

    # Display images with bounding boxes in a 3-column grid
    images = draw_bounding_boxes(image_dir, filtered_data)

    if not images:
        st.info("No valid images to display.")
    else:
        num_columns = 3
        columns = st.columns(num_columns)

        for idx, (file_name, image) in enumerate(images):
            with columns[idx % num_columns]:
                st.image(image, use_container_width=True, caption=f"{file_name}")