import streamlit as st
from st_copy_to_clipboard import st_copy_to_clipboard
from utils import *

# Set wide page layout
st.set_page_config(page_title="Cluster Visualization App", layout="wide")

# Streamlit app
st.title("Cluster Visualization App")

# Initialize session state for selected cluster and checkboxes
if "selected_cluster_label" not in st.session_state:
    st.session_state.selected_cluster_label = None
if "show_multiple_faces_only" not in st.session_state:
    st.session_state.show_multiple_faces_only = False
if "show_face_ids" not in st.session_state:
    st.session_state.show_face_ids = True  # Default to showing Face IDs

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
        cols = st.sidebar.columns(3)
        for i in range(1, 4):
            thumbnail_key = f"thumbnail_{i}"
            if thumbnail_key in cluster:
                thumbnail = decode_base64_image(cluster[thumbnail_key])
                if thumbnail:
                    with cols[i - 1]:
                        st.image(thumbnail, use_container_width=True)
            else:
                with cols[i - 1]:
                    st.write("No thumbnail available")

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

    # Checkbox for filters and toggles
    show_multiple_faces = st.checkbox(
        "Show Images with Multiple Faces Only",
        value=st.session_state.show_multiple_faces_only,
    )
    st.session_state.show_multiple_faces_only = show_multiple_faces

    show_face_ids = st.checkbox(
        "Show Face ID",
        value=st.session_state.show_face_ids,
    )
    st.session_state.show_face_ids = show_face_ids

    # Filter images if checkbox is checked
    filtered_data = {
        file_name: data for file_name, data in image_data.items()
        if not st.session_state.show_multiple_faces_only or data["has_multiple_faces"]
    }

    # Main area: Display Cluster Label and Size
    st.header(f"Cluster {selected_cluster_label} (Size: {cluster_size})")
    if st.session_state.show_multiple_faces_only and not filtered_data:
        st.info("No images with multiple faces in this cluster.")

    # Main area: Display images with bounding boxes
    images = draw_bounding_boxes_with_colors(image_dir, filtered_data)

    if not images:
        st.info("No valid images to display.")
    else:
        num_columns = 3
        columns = st.columns(num_columns)

        for idx, (file_name, image, clickable_regions) in enumerate(images):
            with columns[idx % num_columns]:
                st.image(image, use_container_width=True, caption=f"{file_name}")

                if st.session_state.show_face_ids:
                    for face_id, cords, color in clickable_regions:
                        col1, col2, col3 = st.columns([2, 1, 1])

                        with col1:
                            st.markdown(
                                f"<span style='color: {color}; font-weight: bold;'>Face ID: {face_id}</span>",
                                unsafe_allow_html=True,
                            )
                        with col2:
                            st_copy_to_clipboard(
                                text=face_id,
                                before_copy_label="📋 Copy",
                                after_copy_label="✅ Copied!",
                                key=f"copy_{file_name}_{face_id}",
                            )
                        with col3:
                            if st.button("Details", key=f"details_{file_name}_{face_id}"):
                                face_data = next(
                                    face for face in selected_data["faces"]
                                    if face["face_id"] == face_id
                                )

                                face_info = {
                                    "cluster_label": selected_cluster_label,
                                    "cluster_size": cluster_size,
                                    "face_id": face_id,
                                    "file_name": file_name,
                                    "cords": face_data["cords"],
                                    "width": face_data["cords"][2] - face_data["cords"][0],
                                    "height": face_data["cords"][3] - face_data["cords"][1],
                                    "alignment_method": face_data.get("alignment_method", "N/A"),
                                    "score": face_data.get("score", "N/A"),
                                    "blur_score": face_data.get("blur_score", "N/A")
                                }
                                show_face_details(face_info)