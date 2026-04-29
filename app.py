"""
Streamlit Frontend for Name Card Extraction - Refactored Version

This application provides a user-friendly web interface for extracting information
from business name cards using AI-powered image analysis.

Features:
- Upload single or multiple name card images
- Take photos directly with camera (single or batch)
- Real-time image preview with zoom functionality
- AI-powered extraction of business card information
- Interactive results display with editing capabilities
- Export results to Excel and JSON formats
- Batch processing for multiple images
- Image format support: JPG, PNG, JPEG
- Camera capture with live preview

Author: Name Card Extraction Team
"""

import streamlit as st
import pandas as pd
import json
import os
import tempfile
import time
from datetime import datetime
from PIL import Image
import io
import base64
from typing import List, Dict, Any

# Import extraction service
from namecard_service import NameCardExtractor, append_results_to_csv

# Page configuration
st.set_page_config(
    page_title="Name Card Information Extractor",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"  # Start with sidebar expanded
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    
    .sub-header {
        font-size: 1.5rem;
        color: #374151;
        margin-bottom: 1rem;
    }
    
    .stButton > button {
        background-color: #3B82F6;
        color: white;
        border-radius: 0.5rem;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: bold;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        background-color: #2563EB;
        transform: translateY(-2px);
    }
    
    .failed-image-container {
        border: 2px solid #EF4444;
        border-radius: 0.5rem;
        padding: 1rem;
        background-color: #FEF2F2;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    defaults = {
        'extracted_data': [],
        'processing_complete': False,
        'current_image_index': 0,
        'confirmed': False,
        'top_confirmed': False,
        'add_new_mode': False,
        'camera_batch': [],
        'show_samples': False,
        'active_tab': 0,
        'last_saved_count': 0,
        'pending_csv_save': False,
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def get_successful_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    successful_results = []
    for result in results:
        if result.get('status') != 'success' or 'data' not in result:
            continue
        data = result['data']
        non_empty_fields = [v for v in data.values() if v and str(v).strip()]
        if non_empty_fields:
            successful_results.append(result)
    return successful_results


def save_results_to_master_csv(results: List[Dict[str, Any]]) -> int:
    saved_count = append_results_to_csv(results)
    st.session_state.last_saved_count = saved_count
    return saved_count

def validate_image(uploaded_file) -> bool:
    """Validate uploaded image file"""
    try:
        if hasattr(uploaded_file, 'seek'):
            uploaded_file.seek(0)
        
        image = Image.open(uploaded_file)
        
        # Check file size (max 10MB)
        file_size = getattr(uploaded_file, 'size', len(uploaded_file.getvalue()) if hasattr(uploaded_file, 'getvalue') else 0)
        if file_size > 10 * 1024 * 1024:
            st.error("File size too large. Please upload images smaller than 10MB.")
            return False
        
        # Check image dimensions
        # if image.width > 4000 or image.height > 4000:
        #     st.warning("Large image detected. Processing may take longer.")
        
        return True
    except Exception as e:
        st.error(f"Invalid image file: {str(e)}")
        return False

def get_active_provider_name() -> str:
    provider = os.getenv("AI_PROVIDER", "watsonx").strip().lower()
    provider_labels = {
        "watsonx": "IBM Watsonx",
        "openai": "OpenAI",
        "azure_openai": "Azure OpenAI",
        "gemini": "Google Gemini",
        "openai_compatible": "OpenAI-Compatible / On-Prem",
    }
    return provider_labels.get(provider, provider)


def process_single_image(uploaded_file, progress_bar=None) -> Dict[str, Any]:
    """Process a single name card image with failed image storage capability"""
    tmp_file_path = ""
    image_data = b""
    file_extension = 'jpg'

    try:
        if hasattr(uploaded_file, 'seek'):
            uploaded_file.seek(0)

        filename = getattr(uploaded_file, 'name', 'camera_capture.jpg')
        image_data = uploaded_file.getvalue()

        if hasattr(uploaded_file, 'name') and '.' in uploaded_file.name:
            file_extension = uploaded_file.name.split('.')[-1]

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as tmp_file:
            tmp_file.write(image_data)
            tmp_file_path = tmp_file.name
        
        # Progress updates
        provider_name = get_active_provider_name()

        if progress_bar:
            progress_bar.progress(25, f"Initializing {provider_name} extractor...")

        extractor = NameCardExtractor(image_input_path=tmp_file_path)

        if progress_bar:
            progress_bar.progress(50, f"Extracting information with {provider_name}...")
        
        result = extractor.run()
        
        if progress_bar:
            progress_bar.progress(75, "Processing results...")
        
        # Parse result
        parsed_result = json.loads(result) if isinstance(result, str) else result
        
        # Check if there's an error in the result
        if 'error' in parsed_result:
            os.unlink(tmp_file_path)
            error_message = parsed_result['error']
            
            if "missing" in error_message.lower() and ".env" in error_message.lower():
                error_message = f"{provider_name} configuration is missing in [.env](.env)."
            
            return {
                'filename': filename,
                'status': 'error',
                'error': error_message,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_data': image_data,  # Store failed image for retry
                'image_format': file_extension
            }
        
        # Check if all fields are empty
        non_empty_fields = [v for v in parsed_result.values() if v and v.strip() and v != '']
        
        if not non_empty_fields:
            if progress_bar:
                progress_bar.progress(100, "Complete - No data extracted")
            
            os.unlink(tmp_file_path)
            return {
                'filename': filename,
                'status': 'error',
                'error': 'No information could be extracted from the image. All fields are empty.',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'image_data': image_data,  # Store failed image for retry
                'image_format': file_extension
            }
        
        if progress_bar:
            progress_bar.progress(100, "Complete!")
        
        os.unlink(tmp_file_path)
        
        return {
            'filename': filename,
            'status': 'success',
            'data': parsed_result,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        if tmp_file_path:
            try:
                os.unlink(tmp_file_path)
            except OSError:
                pass

        filename = getattr(uploaded_file, 'name', 'camera_capture.jpg')
        error_message = str(e)

        provider_name = get_active_provider_name()
        if "missing" in error_message.lower() and ".env" in error_message.lower():
            error_message = f"{provider_name} configuration is missing in [.env](.env)."

        return {
            'filename': filename,
            'status': 'error',
            'error': error_message,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'image_data': image_data,
            'image_format': file_extension
        }

def process_batch_images(files, progress_container):
    """Process multiple images in batch"""
    valid_files = [f for f in files if validate_image(f)]

    if not valid_files:
        st.error("No valid files to process.")
        return []

    progress_bar = progress_container.progress(0, "Starting batch processing...")
    results = []

    for idx, file in enumerate(valid_files):
        progress = (idx + 1) / len(valid_files)
        progress_bar.progress(progress, f"Processing {getattr(file, 'name', f'File {idx+1}')} ({idx + 1}/{len(valid_files)})")

        result = process_single_image(file)
        results.append(result)

    progress_bar.empty()
    return results


def finalize_processed_results(results: List[Dict[str, Any]], replace_existing: bool = True):
    """Store results in session state and mark them for CSV save after confirmation."""
    if replace_existing:
        st.session_state.extracted_data = results
    else:
        st.session_state.extracted_data.extend(results)

    st.session_state.processing_complete = bool(st.session_state.extracted_data)
    st.session_state.confirmed = False
    st.session_state.top_confirmed = False
    st.session_state.pending_csv_save = bool(get_successful_results(st.session_state.extracted_data))

def display_processing_results(results):
    """Display processing completion message and animation"""
    successful = len([r for r in results if r['status'] == 'success'])
    failed = len([r for r in results if r['status'] == 'error'])
    total = len(results)
    
    if failed > 0:
        # Show errors if any failed
        st.error(f"❌ {failed}/{total} images failed to process. Check the Results tab for details.")
        
        # Show first error for context
        first_error = next((r for r in results if r['status'] == 'error'), None)
        if first_error and 'error' in first_error:
            error_msg = first_error['error']
            if "400 Client Error" in error_msg or "Bad Request" in error_msg:
                st.error("🔑 **Configuration Error**: Please check the active provider settings in `.env`.")
            elif "timeout" in error_msg.lower():
                st.error("⏱️ **Timeout Error**: Processing took too long. Please try again.")
            else:
                st.error(f"**Error Details**: {error_msg}")
    
    if successful > 0:
        st.success(f"✅ {successful}/{total} images processed successfully, please go to the Results Tab.")
        if successful == total:
            st.balloons()
    elif total > 0:
        st.error(f"❌ All {total} images failed to process.")



def display_image_with_info(uploaded_file):
    """Display image with information"""
    if hasattr(uploaded_file, 'seek'):
        uploaded_file.seek(0)
    
    image = Image.open(uploaded_file)
    filename = getattr(uploaded_file, 'name', 'Camera Capture')
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.image(image, caption=f"📄 {filename}", use_container_width=True)
    
    with col2: # Display image information
        st.markdown("### 📋 Image Information")
        file_size = getattr(uploaded_file, 'size', len(uploaded_file.getvalue()) if hasattr(uploaded_file, 'getvalue') else 0)
        
        st.markdown(f"**Filename:** {filename}")
        st.markdown(f"**Size:** {file_size:,} bytes")
        st.markdown(f"**Dimensions:** {image.width} × {image.height} pixels")
        st.markdown(f"**Format:** {image.format}")


def display_batch_image_gallery(uploaded_files):
    """Display all uploaded images in a responsive multi-column gallery."""
    if not uploaded_files:
        return

    st.markdown(f"### 🖼️ Uploaded Images ({len(uploaded_files)})")
    columns_per_row = 3

    for start_index in range(0, len(uploaded_files), columns_per_row):
        row_files = uploaded_files[start_index:start_index + columns_per_row]
        columns = st.columns(columns_per_row)

        for column, uploaded_file in zip(columns, row_files):
            if hasattr(uploaded_file, 'seek'):
                uploaded_file.seek(0)

            image = Image.open(uploaded_file)
            filename = getattr(uploaded_file, 'name', f'Image {start_index + 1}')
            file_size = getattr(
                uploaded_file,
                'size',
                len(uploaded_file.getvalue()) if hasattr(uploaded_file, 'getvalue') else 0,
            )

            with column:
                st.image(image, caption=f"📄 {filename}", use_container_width=True)
                st.caption(
                    f"{file_size:,} bytes • {image.width} × {image.height} px • "
                    f"{(image.format or 'Unknown').upper()}"
                )

def get_input_method_selection(key_prefix=""):
    """Get user's input method selection (upload vs camera)"""
    return st.radio(
        "How would you like to provide the name card image?",
        ["📁 Upload Image File", "📷 Take Photo with Camera"],
        horizontal=True,
        key=f"{key_prefix}_input_method"
    )

def get_file_upload(key_suffix="", multiple=False):
    """Get file upload widget"""
    label = "Choose name card images" if multiple else "Choose a name card image"
    help_text = "Upload business name card images" + (" for batch processing" if multiple else "")
    
    return st.file_uploader(
        label,
        type=['png', 'jpg', 'jpeg'],
        accept_multiple_files=multiple,
        help=help_text,
        key=f"file_upload_{key_suffix}"
    )

def get_camera_input(label="Take a photo of the name card", key_suffix=""):
    """Get camera input widget with tips"""
    st.info("💡 **Camera Tips:**\n"
           "- Ensure good lighting\n"
           "- Hold the camera steady\n"
           "- Make sure the name card fills most of the frame\n"
           "- Avoid glare and shadows")
    
    return st.camera_input(
        label,
        help="Position the name card clearly in the camera view and click the capture button",
        key=f"camera_{key_suffix}"
    )

def create_camera_file_object(camera_image, timestamp=None):
    """Create a file-like object from camera image"""
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    camera_file_name = f"camera_capture_{timestamp}.jpg"
    
    class CameraFile:
        def __init__(self, data, name, size):
            self.data = io.BytesIO(data)
            self.name = name
            self.size = size
        
        def getvalue(self):
            return self.data.getvalue()
        
        def read(self, size=-1):
            return self.data.read(size)
        
        def readline(self, size=-1):  # Add this method
            return self.data.readline(size)
        
        def readlines(self, hint=-1):  # Add this method
            return self.data.readlines(hint)
        
        def seek(self, pos, whence=0):  # Update to accept whence parameter
            return self.data.seek(pos, whence)
        
        def tell(self):  # Add this method
            return self.data.tell()
        
        def close(self):  # Add this method
            return self.data.close()
    
    return CameraFile(camera_image.getvalue(), camera_file_name, len(camera_image.getvalue()))

def display_extraction_results(results: List[Dict[str, Any]]):
    """Display extraction results with failed image display and retry functionality"""
    if not results:
        st.info("No results to display.")
        return
    
    total_processed = len(results)
    successful = len([r for r in results if r['status'] == 'success'])
    failed = total_processed - successful
    
    # Count successful results with actual data
    successful_with_data = 0
    for r in results:
        if r['status'] == 'success' and 'data' in r:
            data = r['data']
            non_empty_fields = [v for v in data.values() if v and str(v).strip()]
            if non_empty_fields:
                successful_with_data += 1
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Processed", total_processed)
    col2.metric("Successful", successful)
    col3.metric("Failed", failed)
    
    # Detailed results
    for idx, result in enumerate(results):
        with st.expander(f"📄 {result['filename']} - {result['status'].title()}", expanded=True):
            if result['status'] == 'success':
                display_editable_result(result, idx)
            else:
                # Display failed result with image and retry functionality
                st.error(f"❌ Processing failed: {result.get('error', 'Unknown error')}")
                
                # Show the failed image if available
                if 'image_data' in result and result['image_data']:
                    try:
                        image = Image.open(io.BytesIO(result['image_data']))
                        col1, col2 = st.columns([2, 1])
                        
                        with col1:
                            st.image(image, caption=f"❌ Failed: {result['filename']}", use_container_width=True)
                        
                        with col2:
                            st.markdown("**📋 Image Info:**")
                            st.write(f"**Size:** {len(result['image_data']):,} bytes")
                            st.write(f"**Dimensions:** {image.width} × {image.height} px")
                            st.write(f"**Format:** {result.get('image_format', 'Unknown').upper()}")
                            
                            # Retry button
                            if st.button(f"🔄 Retry Processing", key=f"retry_{idx}", type="primary"):
                                retry_failed_image(result, idx)
                            
                            # Download button for failed image
                            st.download_button(
                                label="📥 Download Failed Image",
                                data=result['image_data'],
                                file_name=result['filename'],
                                mime=f"image/{result.get('image_format', 'jpg')}",
                                key=f"download_{idx}",
                                help="Download the original image that failed processing",
                                use_container_width=True
                            )
                    
                    except Exception as e:
                        st.warning(f"Could not display failed image: {str(e)}")
                else:
                    st.info("No image data available for this failed result.")
            
            st.markdown(f"*Processed at: {result['timestamp']}*")

def retry_failed_image(result, idx):
    """Retry processing a single failed image"""
    try:
        # Create file object and retry
        class SimpleRetry:
            def __init__(self, data, name):
                self.data = io.BytesIO(data)
                self.name = name
                self.size = len(data)
            
            def getvalue(self): 
                return self.data.getvalue()
            
            def read(self, size=-1): 
                return self.data.read(size)
            
            def seek(self, pos, whence=0): 
                return self.data.seek(pos, whence)
        
        retry_file = SimpleRetry(result['image_data'], result['filename'])
        
        with st.spinner("🔄 Retrying image processing..."):
            progress_bar = st.progress(0, "Retrying...")
            new_result = process_single_image(retry_file, progress_bar)
            
            # Update the result in session state
            st.session_state.extracted_data[idx] = new_result
            progress_bar.empty()
            
        if new_result['status'] == 'success':
            st.success("✅ Retry successful! Image processed successfully.")
            st.balloons()
            time.sleep(1)
            st.rerun()
        else:
            st.error(f"❌ Retry failed: {new_result.get('error', 'Unknown error')}")
            
    except Exception as e:
        st.error(f"Error during retry: {str(e)}")

# def render_top_confirm_button():
#     """Render additional confirm button at the top of results"""
#     confirmed = st.session_state.get('confirmed', False)
    
#     col1, col2, col3 = st.columns([1, 2, 1])
    
#     with col2:
#         if not confirmed:
#             if st.button("Confirm All Results", type="primary", use_container_width=True, key="top_confirm"):
#                 st.session_state.confirmed = True
#                 st.success("All results confirmed! You can now export your data.")
#                 st.rerun()
#         else:
#             st.success("All results have been confirmed!")

def display_editable_result(result, idx):
    """Display editable form for a single result"""
    data = result['data']
    
    with st.form(key=f"edit_form_{idx}"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🏢 Company Information")
            company_name = st.text_input("Company Name", value=data.get('Company_Name', ''), key=f"company_{idx}_edit")
            company_website = st.text_input("Website", value=data.get('Company_Website', ''), key=f"website_{idx}_edit")
            address = st.text_area("Address", value=data.get('Address', ''), key=f"address_{idx}_edit")
        
        with col2:
            st.markdown("#### 👤 Contact Information")
            name = st.text_input("Name", value=data.get('Name', ''), key=f"name_{idx}_edit")
            title = st.text_input("Title", value=data.get('Title', ''), key=f"title_{idx}_edit")
            email = st.text_input("Email", value=data.get('Email', ''), key=f"email_{idx}_edit")
        
        st.markdown("#### 📞 Phone Numbers")
        phone_col1, phone_col2, phone_col3, phone_col4 = st.columns(4)
        
        with phone_col1:
            telephone = st.text_input("Telephone", value=data.get('Telephone', ''), key=f"tel_{idx}_edit")
        with phone_col2:
            direct = st.text_input("Direct", value=data.get('Direct', ''), key=f"direct_{idx}_edit")
        with phone_col3:
            mobile = st.text_input("Mobile", value=data.get('Mobile', ''), key=f"mobile_{idx}_edit")
        with phone_col4:
            fax = st.text_input("Fax", value=data.get('Fax', ''), key=f"fax_{idx}_edit")
        
        # Save button
        if st.form_submit_button("💾 Save Changes"):
            st.session_state.extracted_data[idx]['data'] = {
                'Company_Name': company_name,
                'Company_Website': company_website,
                'Address': address,
                'Name': name,
                'Title': title,
                'Email': email,
                'Telephone': telephone,
                'Direct': direct,
                'Mobile': mobile,
                'Fax': fax
            }
            st.session_state.confirmed = False
            st.session_state.top_confirmed = False  # Reset top confirm state
            st.success("Changes saved for this business card. Please confirm all results again to enable export.")
            time.sleep(0.5)
            st.rerun()
    
    # Raw JSON display
    # with st.expander("🔍 Raw JSON Data"):
    #     st.json(st.session_state.extracted_data[idx]['data'])


def render_control_buttons():
    """Render the control buttons row"""
    confirmed = st.session_state.get('confirmed', False)
    st.markdown("---")
    
    # Create centered layout - empty space, two buttons, empty space
    col1, col2, col3, col4 = st.columns([2, 1.5, 1.5, 2])
    
    with col1:
        pass  # Left spacing
    
    with col2:
        if st.button("🗑️ Clear Results", use_container_width=True):
            reset_session_data()
            st.session_state.active_tab = 1  # Go back to Results tab
            st.rerun()
            
    
    with col3:
        if not confirmed:
            if st.button("✅Confirm", use_container_width=True):
                confirm_and_save_results()
                st.rerun()
                
                
        else:
            st.success("✅Confirmed")
    
    with col4:
        pass  # Right spacing
            
def confirm_and_save_results():
    """Confirm results and append successful records to the master CSV once."""
    st.session_state.confirmed = True
    st.session_state.top_confirmed = True
    st.session_state.active_tab = 2  # Go to Export tab

    if st.session_state.get('pending_csv_save', False):
        successful_results = get_successful_results(st.session_state.extracted_data)
        if successful_results:
            saved_count = save_results_to_master_csv(successful_results)
            st.session_state.pending_csv_save = False
            st.success(
                f"✅ All results confirmed! 📁 {saved_count} record(s) appended to "
                f"[namecard_results.csv](namecard_results.csv)."
            )
            return

    st.success("✅ All results confirmed! You can now export your data.")


def render_top_confirm_button():
    """Render additional confirm button at the top of results"""
    confirmed = st.session_state.get('top_confirmed', False)
    
    # Create a centered layout for the top confirm button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if not confirmed:
            if st.button("✅ Confirm All Results", type="primary", use_container_width=True, key="top_confirm"):
                confirm_and_save_results()
                st.rerun()
        else:
            st.success("✅ All results have been confirmed!")
    
    st.markdown("---")  # Add separator after top button

def reset_session_data():
    """Reset session data to initial state"""
    st.session_state.extracted_data = []
    st.session_state.processing_complete = False
    st.session_state.confirmed = False
    st.session_state.add_new_mode = False
    st.session_state.pending_csv_save = False

def render_add_new_namecard_section():
    """Render the add new namecard section"""
    st.markdown("---")
    st.markdown("### ➕ Add More Name Cards")
    st.info("Add new name cards to your existing results without losing current data")
    
    if not st.session_state.add_new_mode:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("➕ Add New Name Card", type="primary", use_container_width=True):
                st.session_state.add_new_mode = True
                st.rerun()
        # with col2:
        #     st.markdown("*Click to add additional name cards to your current results*")
    else:
        render_add_new_interface()

def render_add_new_interface():
    """Render the interface for adding new name cards"""
    st.markdown("#### 🆕 Add New Name Card")
    
    input_method = get_input_method_selection("new_card")
    current_image = None
    
    if input_method == "📁 Upload Image File":
        current_image = get_file_upload("new_card")
    else:
        current_image = get_camera_input("Take a photo of the new name card", "new_card")
    
    if current_image is not None:
        if validate_image(current_image):
            display_image_with_info(current_image)
            
            process_col1, process_col2, process_col3 = st.columns(3)
            
            with process_col1:
                if st.button("🔍 Process This Card", type="primary", use_container_width=True):
                    progress_bar = st.progress(0, "Processing new name card...")

                    with st.spinner("Extracting information from new card..."):
                        new_result = process_single_image(current_image, progress_bar)
                        finalize_processed_results([new_result], replace_existing=False)

                    time.sleep(0.5)
                    progress_bar.empty()

                    if new_result['status'] == 'success':
                        st.success("✅ New name card processed successfully!")
                        st.balloons()
                        st.session_state.add_new_mode = False
                        st.rerun()
                    else:
                        st.error(f"❌ Processing failed: {new_result.get('error', 'Unknown error')}")
            
            with process_col2:
                if st.button("❌ Cancel", type="secondary", use_container_width=True):
                    st.session_state.add_new_mode = False
                    st.rerun()
            
            with process_col3:
                st.info("Process the card to add it to your results")
    
    if current_image is None:
        if st.button("❌ Cancel Adding New Card", type="secondary"):
            st.session_state.add_new_mode = False
            st.rerun()

def render_batch_upload_section():
    """Render batch file upload section"""
    uploaded_files = get_file_upload("batch", multiple=True)
    
    if uploaded_files:
        display_batch_image_gallery(uploaded_files)

        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔍 Extract All Information", type="primary", use_container_width=True):
                results = process_batch_images(uploaded_files, st)

                if results:
                    finalize_processed_results(results, replace_existing=True)
                    display_processing_results(results)

def render_camera_batch_section():
    """Render camera batch processing section"""
    # st.markdown("### 📷 Multiple Camera Captures")
    st.info("**Camera Batch Processing:**\n"
           "- Take photos one by one\n"
           "- Each photo will be added to the batch\n"
           "- Process all photos together when ready")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        camera_image = st.camera_input(
            f"Take photo #{len(st.session_state.camera_batch) + 1}",
            help="Position the name card clearly and capture"
        )
        
        if camera_image is not None:
            if st.button("➕ Add to Batch", type="secondary"):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                camera_file_data = {
                    'name': f"camera_capture_{timestamp}.jpg",
                    'data': camera_image.getvalue(),
                    'size': len(camera_image.getvalue()),
                    'type': 'image/jpeg'
                }
                
                st.session_state.camera_batch.append(camera_file_data)
                st.success(f"📷 Photo added to batch! Total: {len(st.session_state.camera_batch)} images")
                st.rerun()
    
    with col2:
        render_camera_batch_controls()

def render_camera_batch_controls():
    """Render camera batch control buttons"""
    st.markdown("#### 📋 Current Batch")
    
    if st.session_state.camera_batch:
        st.markdown(f"**Images in batch:** {len(st.session_state.camera_batch)}")
        
        for idx, img_data in enumerate(st.session_state.camera_batch, 1):
            st.markdown(f"{idx}. {img_data['name']}")
        
        if st.button("🗑️ Clear Batch", type="secondary"):
            st.session_state.camera_batch = []
            st.rerun()
        
        if st.button("🔍 Process Batch", type="primary"):
            camera_files = [create_camera_file_object(io.BytesIO(img['data']), img['name'].split('_')[-1].split('.')[0])
                           for img in st.session_state.camera_batch]

            results = process_batch_images(camera_files, st)

            if results:
                finalize_processed_results(results, replace_existing=True)
                st.session_state.camera_batch = []
                display_processing_results(results)
    else:
        st.info("No images in batch yet. Take a photo and add it to start building your batch.")

def export_to_excel(results: List[Dict[str, Any]]) -> bytes | None:
    """Export results to Excel format - only include successful extractions with data"""
    successful_results = get_successful_results(results)

    if not successful_results:
        return None
    
    records = []
    for result in successful_results:
        record = result['data'].copy()
        record['Filename'] = result['filename']
        record['Processing_Timestamp'] = result['timestamp']
        records.append(record)
    
    columns = [
        'Company_Name', 'Name', 'Title', 'Telephone', 
        'Direct', 'Mobile', 'Fax', 'Email', 'Address', 'Company_Website', 
        'Processing_Timestamp','Filename',
    ]
    
    df = pd.DataFrame(records)
    available_columns = [col for col in columns if col in df.columns]
    extra_columns = [col for col in df.columns if col not in columns]
    df = df[available_columns + extra_columns]
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp_excel:
        temp_excel_path = tmp_excel.name

    try:
        df.to_excel(temp_excel_path, sheet_name='Name Card Data', index=False, engine='openpyxl')
        with open(temp_excel_path, "rb") as excel_file:
            return excel_file.read()
    finally:
        if os.path.exists(temp_excel_path):
            os.unlink(temp_excel_path)

def export_to_json(results: List[Dict[str, Any]]) -> str:
    """Export results to JSON format - excluding binary image data"""
    # Create a copy of results without binary data
    json_safe_results = []
    
    for result in results:
        json_safe_result = result.copy()
        
        # Remove binary data that can't be serialized to JSON
        if 'image_data' in json_safe_result:
            # Remove binary data completely for JSON export
            del json_safe_result['image_data']
            
            # Optionally, you could convert to base64 string instead:
            # import base64
            # json_safe_result['image_data_base64'] = base64.b64encode(json_safe_result['image_data']).decode('utf-8')
            # del json_safe_result['image_data']
        
        json_safe_results.append(json_safe_result)
    
    return json.dumps(json_safe_results, indent=2, ensure_ascii=False)

def render_sidebar():
    """Render the sidebar content"""
    with st.sidebar:
        # st.markdown("### 🛠️ Settings")
        
        st.markdown("### ℹ️ Information")
        st.markdown(f"""
        **Active AI Provider:**
        - {get_active_provider_name()}

        **Provider Source:**
        - `AI_PROVIDER` from `.env`

        **File Requirements:**
        - Max file size: 10MB

        **Extracted Information:**
        - Company Name
        - Name
        - Title
        - Contact
        - Email Address
        - Physical Address
        - Company Website
        """)
        
        # Custom CSS for button styling
        st.markdown("""
        <style>
        div[data-testid="stSidebar"] button[data-testid="baseButton"] {
            font-size: 0.85rem !important;
            padding: 0.2rem 0.7rem !important;
            height: 2rem !important;
            min-height: 2rem !important;
        }
        
        /* Style for active sample button */
        .sample-button-active {
            background-color: #DBEAFE !important; /* Pale blue background */
            color: #1E40AF !important; /* Darker blue text */
            border: 1px solid #93C5FD !important; /* Light blue border */
        }
        
        .sample-button-active:hover {
            background-color: #BFDBFE !important; /* Slightly darker on hover */
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown("### Sample Image")
        
        # Check if samples are currently showing
        show_samples = st.session_state.get('show_samples', False)
        
        # Button text changes based on state
        button_text = "Sample Image" if show_samples else "Sample Image"
        button_type = "secondary" if show_samples else "primary"
        
        if st.button(button_text, key="sample_btn", type=button_type):
            # Toggle the sample display state
            st.session_state.show_samples = not st.session_state.show_samples
            st.rerun()

def render_export_tab():
    """Render the export tab content"""
    st.markdown('<h3 class="sub-header">Export Results</h3>', unsafe_allow_html=True)
    confirmed = st.session_state.get('confirmed', False)
    
    if not confirmed:
        st.warning("Please confirm your results in the **Results** tab before exporting.")
    elif st.session_state.processing_complete and st.session_state.extracted_data:
        render_export_options()
    else:
        st.info("Process some name card images first to enable export options.")

def render_export_options():
    """Render export options and preview"""
    successful_with_data = get_successful_results(st.session_state.extracted_data)
    
    if successful_with_data:
        total_results = len(st.session_state.extracted_data)
        exportable_results = len(successful_with_data)
        
        # if exportable_results < total_results:
        #     st.info(f"**Export Info:** {exportable_results} out of {total_results} processed images contain extractable data and will be included in exports.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            render_excel_export_section(successful_with_data, exportable_results)
        
        with col2:
            render_json_export_section(total_results)
        
        render_export_preview(successful_with_data, total_results)
    else:
        st.warning("⚠️ No successful extractions to export. Please process some images first.")

def render_excel_export_section(successful_with_data, count):
    """Render Excel export section"""
    st.markdown("#### 📋 Excel Export")
    # st.markdown("Export structured data to Excel format for further analysis")
    # st.markdown(f"*Will export {count} records with data*")
    
    excel_data = export_to_excel(st.session_state.extracted_data)
    if excel_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            label="📥 Download Excel File",
            data=excel_data,
            file_name=f"namecard_results_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    else:
        st.warning("No data available for Excel export")

def render_json_export_section(total_results):
    """Render JSON export section"""
    st.markdown("#### 🔧 JSON Export")
    # st.markdown("Export raw data in JSON format for integration")
    # st.markdown(f"*Will export all {total_results} processing results*")
    
    json_data = export_to_json(st.session_state.extracted_data)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        label="📥 Download JSON File",
        data=json_data,
        file_name=f"namecard_results_{timestamp}.json",
        mime="application/json",
        use_container_width=True
    )

def render_export_preview(successful_with_data, total_results):
    """Render export preview section"""
    st.markdown("#### 👀 Preview")
    preview_format = st.selectbox("Choose preview format:", ["Excel Preview", "JSON Preview"])
    
    if preview_format == "Excel Preview":
        if successful_with_data:
            records = []
            for result in successful_with_data:
                record = result['data'].copy()
                record['Filename'] = result['filename']
                records.append(record)
            df = pd.DataFrame(records)
            st.dataframe(df, use_container_width=True)
            st.info(f"Preview shows {len(records)} records with extractable data")
        else:
            st.warning("No records with data available for Excel preview")
    else:
        st.json(st.session_state.extracted_data)
        st.info(f"JSON preview shows all {total_results} processing results")

# def render_sample_images():
#     """Render sample images section - only show specific example"""
#     if st.session_state.get('show_samples', False):
#         with st.expander("Sample Name Card Image", expanded=True):
#             try:
#                 sample_path = "./Sample/"
#                 target_file = "Your paragraph text.png"
                
#                 if os.path.exists(sample_path):
#                     img_path = os.path.join(sample_path, target_file)
                    
#                     if os.path.exists(img_path):
#                         try:
#                             image = Image.open(img_path)
#                             st.image(image, caption=target_file, width=720)
#                             st.info("This is an example of a name card image that works well with the extraction system.")
#                         except Exception as e:
#                             st.error(f"Could not load {target_file}: {str(e)}")
#                     else:
#                         st.warning(f"Example file '{target_file}' not found in ./Sample/ directory")
#                 else:
#                     st.info("Sample directory not found")
#             except Exception as e:
#                 st.error(f"Error loading sample image: {str(e)}")
            
#             if st.button("Close Sample"):
#                 st.session_state.show_samples = False
#                 st.rerun()
def render_sample_images():
    """Render sample images section - only show specific example"""
    if st.session_state.get('show_samples', False):
        with st.expander("Sample Name Card Image", expanded=True):
            try:
                sample_path = "./Sample/"
                target_file = "Your paragraph text.png"
                
                if os.path.exists(sample_path):
                    img_path = os.path.join(sample_path, target_file)
                    
                    if os.path.exists(img_path):
                        try:
                            image = Image.open(img_path)
                            
                            # Add responsive CSS for sample image
                            st.markdown("""
                            <style>
                                .responsive-sample-image {
                                    width: 720px;
                                    height: auto;
                                    max-width: 100%;
                                }
                                
                                /* Mobile devices (smartphones) */
                                @media (max-width: 768px) {
                                    .responsive-sample-image {
                                        width: 480px !important;
                                    }
                                }
                            </style>
                            """, unsafe_allow_html=True)
                            
                            # Convert image to base64 for HTML embedding
                            img_buffer = io.BytesIO()
                            image.save(img_buffer, format='PNG')
                            img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
                            
                            # Display with responsive CSS class
                            st.markdown(f"""
                            <img src="data:image/png;base64,{img_base64}" 
                                 class="responsive-sample-image" 
                                 alt="{target_file}">
                            <p style="text-align: center; color: #666; font-style: italic; margin-top: 10px;">
                                {target_file}
                            </p>
                            """, unsafe_allow_html=True)
                            
                            st.info("This is an example of a name card image that works well with the extraction system.")
                        except Exception as e:
                            st.error(f"Could not load {target_file}: {str(e)}")
                    else:
                        st.warning(f"Example file '{target_file}' not found in ./Sample/ directory")
                else:
                    st.info("Sample directory not found")
            except Exception as e:
                st.error(f"Error loading sample image: {str(e)}")
            
            if st.button("Close Sample"):
                st.session_state.show_samples = False
                st.rerun()

def main():
    """Main application function"""
    st.markdown('''
<style>
    .responsive-header {
        font-size: 3rem;  /* Default h1 size for desktop */
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.5rem;  /* Default h3 size for desktop */
        color: #374151;
        margin-bottom: 1rem;
    }
    @media (max-width: 768px) {
        .responsive-header {
            font-size: 1.6rem !important;
        }
        .sub-header {
            font-size: 1.25rem !important;
        }
    }
    @media (max-width: 1024px) and (min-width: 769px) {
        .responsive-header {
            font-size: 2rem !important;
        }
        .sub-header {
            font-size: 1.375rem !important;
        }
    }
</style>
''', unsafe_allow_html=True)
    initialize_session_state()

    # Add responsive logo and header CSS
    st.markdown("""
<style>
    .responsive-header {
        font-size: 3rem;  /* Default h1 size for desktop */
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 2rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.5rem;  /* Default h3 size for desktop */
        color: #374151;
        margin-bottom: 1rem;
    }
    @media (max-width: 768px) {
        .responsive-header {
            font-size: 1.6rem !important;
        }
        .sub-header {
            font-size: 1.25rem !important;
        }
    }
    @media (max-width: 1024px) and (min-width: 769px) {
        .responsive-header {
            font-size: 2rem !important;
        }
        .sub-header {
            font-size: 1.375rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

    # Header with responsive logo and title
    col_logo, col_title = st.columns([0.5, 9.5])
    with col_title:
        st.markdown('<h1 class="responsive-header">Business Card Automation System</h1>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style='text-align: center; margin-bottom: 2rem; color: #6B7280;'>
            Extract business card information using <strong>file uploads</strong> or <strong>camera capture</strong><br/>
            Active AI provider: <strong>{get_active_provider_name()}</strong>
        </div>
        """, unsafe_allow_html=True)
    
    # Rest of your existing code...
    render_sidebar()
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["🚀 Extract Information", "📊 Results", "📥 Export"])
    
    with tab1:
        st.markdown('<h3 class="sub-header">Upload Name Card Images</h3>', unsafe_allow_html=True)
        #st.markdown("#### 📁 Batch Processing Options")
        
        batch_method = st.radio(
            "Choose input method:",
            ["📁 Upload Files", "📷 Camera Captures"],
            horizontal=True
        )

        if batch_method == "📁 Upload Files":
            render_batch_upload_section()
        else:
            render_camera_batch_section()
    
    with tab2:
        st.markdown('<h3 class="sub-header">Extraction Results</h3>', unsafe_allow_html=True)
        
        if st.session_state.processing_complete and st.session_state.extracted_data:

            render_top_confirm_button()
            display_extraction_results(st.session_state.extracted_data)
            render_control_buttons()
            render_add_new_namecard_section()
        else:
            st.warning("Upload and process name card images in the **Extract Information** tab to see results here.")
    
    with tab3:
        render_export_tab()
    
    # Sample images
    render_sample_images()
    
    # Footer
    st.markdown("---")

if __name__ == "__main__":
    main()

