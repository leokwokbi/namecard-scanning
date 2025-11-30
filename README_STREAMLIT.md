# 💼 Name Card Information Extractor - Streamlit Frontend

A modern, user-friendly web interface for extracting information from business name cards using AI-powered image analysis.

![Name Card Extractor](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![AI](https://img.shields.io/badge/AI-Powered-00D4AA?style=for-the-badge)

## ✨ Features

### 🖼️ Image Processing
- **Single & Batch Processing**: Upload one image or multiple images for batch processing
- **Multiple Formats**: Support for PNG, JPG, and JPEG formats
- **Image Validation**: Automatic validation for file size and format
- **Real-time Preview**: View uploaded images with zoom functionality

### 🤖 AI-Powered Extraction
- **Smart Recognition**: Extract key information from business cards using advanced AI
- **Structured Output**: Organized extraction of company and contact information
- **Error Handling**: Robust error handling with detailed feedback

### 📊 Results Management
- **Interactive Display**: View and edit extracted information in a user-friendly interface
- **Real-time Validation**: Immediate feedback on extraction quality
- **Multiple Export Formats**: Export to Excel and JSON formats
- **Batch Results**: Process multiple cards and view consolidated results

### 🎨 User Experience
- **Modern UI**: Clean, professional interface with responsive design
- **Progress Tracking**: Real-time progress indicators for processing
- **Sample Gallery**: Built-in sample images for testing
- **Accessibility**: Keyboard navigation and screen reader support

## 📋 Information Extracted

The application extracts the following information from name cards:

- **Company Information**
  - Company Name
  - Company Website
  - Physical Address

- **Personal Information**
  - Salesman/Contact Person Name
  - Job Title/Position

- **Contact Details**
  - Telephone Number
  - Direct Line
  - Mobile Number
  - Fax Number
  - Email Address

## 🛠️ Installation & Setup

### Prerequisites

- Python 3.8 or higher
- IBM Watson Machine Learning account and API credentials
- Required Python packages (see requirements.txt)

### Step 1: Clone or Download

```bash
# If using git
git clone <repository-url>
cd namecard

# Or download and extract the project files
```

### Step 2: Install Dependencies

```bash
# Install required packages
pip install -r requirements.txt
```

### Step 3: Environment Configuration

Create a `.env` file in the project directory with your IBM Watson credentials:

```env
WATSONX_API_KEY=your_api_key_here
WATSONX_PROJECT_ID=your_project_id_here
WATSONX_API_URL=https://us-south.ml.cloud.ibm.com
```

### Step 4: Verify Installation

```bash
# Run the quick check
python run_app.py
```

## 🚀 Running the Application

### Method 1: Using the Launcher Script (Recommended)

```bash
python run_app.py
```

This script will:
- ✅ Check all requirements
- ✅ Validate environment configuration
- 🌐 Start the Streamlit server
- 🔗 Open the app in your browser

### Method 2: Direct Streamlit Command

```bash
streamlit run streamlit_app.py
```

### Method 3: Custom Configuration

```bash
streamlit run streamlit_app.py --server.port 8502 --server.headless false
```

## 📱 Using the Application

### 1. Upload Images
- Choose between **Single Image** or **Batch Processing** mode
- Drag and drop or click to upload name card images
- Supported formats: PNG, JPG, JPEG (max 10MB each)

### 2. Extract Information
- Click "🔍 Extract Information" to start processing
- Watch the progress bar for real-time updates
- View results immediately after processing

### 3. Review Results
- Navigate to the **Results** tab to view extracted information
- Edit any fields directly in the interface
- View raw JSON data for technical details

### 4. Export Data
- Go to the **Export** tab for download options
- Choose between Excel (.xlsx) or JSON formats
- Preview data before downloading

## 📁 Project Structure

```
namecard/
├── streamlit_app.py           # Main Streamlit application
├── Name_Card_Extract.py       # Core extraction logic (your existing code)
├── run_app.py                 # Launcher script
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (create this)
├── .streamlit/
│   └── config.toml           # Streamlit configuration
├── Sample/                   # Sample name card images
│   ├── *.jpg
│   └── *.png
└── README_STREAMLIT.md       # This file
```

## ⚙️ Configuration

### Streamlit Configuration (.streamlit/config.toml)

The application includes pre-configured settings for optimal performance:

- **Theme**: Professional blue color scheme
- **Server**: Port 8501 with CORS disabled
- **Browser**: Usage stats disabled for privacy
- **Logging**: Info level for debugging

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `WATSONX_API_KEY` | IBM Watson API Key | ✅ Yes |
| `WATSONX_PROJECT_ID` | IBM Watson Project ID | ✅ Yes |
| `WATSONX_API_URL` | IBM Watson API URL | ✅ Yes |

## 🔧 Troubleshooting

### Common Issues

#### 1. Module Import Errors
```bash
# Solution: Install missing packages
pip install streamlit pandas pillow requests python-dotenv pydantic
```

#### 2. Environment Variable Errors
```bash
# Solution: Check your .env file
cat .env

# Or set variables manually
export WATSONX_API_KEY="your_key_here"
```

#### 3. Port Already in Use
```bash
# Solution: Use a different port
streamlit run streamlit_app.py --server.port 8502
```

#### 4. Image Upload Issues
- Check file size (max 10MB)
- Ensure image format is PNG, JPG, or JPEG
- Verify image is not corrupted

### Performance Tips

1. **Image Optimization**: Resize large images before upload for faster processing
2. **Batch Processing**: Use batch mode for multiple images to improve efficiency
3. **Network**: Ensure stable internet connection for IBM Watson API calls

## 🔐 Security Notes

- Environment variables are kept secure and not exposed in the UI
- Uploaded images are temporarily stored and automatically cleaned up
- API credentials are transmitted securely to IBM Watson services

## 🤝 Integration

### Using with Existing Code

The Streamlit app is designed to work seamlessly with your existing `Name_Card_Extract.py`:

```python
# The app imports and uses your existing extractor
from Name_Card_Extract import NameCardExtractor, NameCardOutput

# Your existing functionality remains unchanged
extractor = NameCardExtractor(image_input_path="path/to/image.jpg")
result = extractor.run()
```

### API Integration

You can also integrate the Streamlit app with your existing FastAPI application:

1. Run both applications on different ports
2. Use the Streamlit app as a frontend dashboard
3. Connect via HTTP requests or shared database

## 📊 Sample Data

The application includes sample name cards in the `Sample/` directory for testing:

- Various business card layouts
- Different languages and formats
- High and low resolution examples

## 🔄 Updates & Maintenance

### Updating Dependencies

```bash
# Update all packages
pip install --upgrade -r req.txt

# Update specific package
pip install --upgrade streamlit
```

### Backup & Recovery

- Export results regularly using the built-in export feature
- Keep your `.env` file secure and backed up
- Save processed results in Excel format for long-term storage

## 📞 Support

### Getting Help

1. **Check the logs**: Look at the Streamlit terminal output for error messages
2. **Verify setup**: Run `python run_app.py` to check your configuration
3. **Test with samples**: Use the built-in sample images to verify functionality
4. **Review documentation**: Check IBM Watson documentation for API issues

### Known Limitations

- Maximum file size: 10MB per image
- Supported formats: PNG, JPG, JPEG only
- Processing time varies based on image complexity and network speed
- Requires internet connection for IBM Watson API access

## 🎯 Future Enhancements

- [ ] Offline processing capability
- [ ] Additional export formats (CSV, PDF)
- [ ] Bulk image upload via folder selection
- [ ] Custom field mapping and validation
- [ ] Integration with CRM systems
- [ ] Multi-language support for extracted text
- [ ] Advanced image preprocessing options

---

**Happy Name Card Extracting! 🚀**
