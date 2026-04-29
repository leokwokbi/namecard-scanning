# Business Card Automation System

A streamlined Streamlit application for extracting information from business cards and storing successful scan results cumulatively in [namecard_results.csv](namecard_results.csv).

The extraction backend supports multiple AI providers controlled by [`AI_PROVIDER`](namecard_service.py:282) in [.env](.env):

- IBM Watsonx
- OpenAI
- Azure OpenAI
- Google Gemini
- OpenAI-compatible on-prem or private endpoints such as Ollama or vLLM

## Project Files

- [app.py](app.py) - Streamlit user interface
- [namecard_service.py](namecard_service.py) - multi-provider extraction logic and cumulative CSV storage
- [.streamlit/config.toml](.streamlit/config.toml) - Streamlit configuration
- [.gitignore](.gitignore) - ignored local files
- [requirements.txt](requirements.txt) - Python dependencies
- [.env.example](.env.example) - example provider configuration template

## Requirements

- Python 3.10+ recommended
- One configured AI provider in [.env](.env)
- Copy [.env.example](.env.example) to [.env](.env) before first run

## Install

Create and activate a virtual environment if desired, then install dependencies:

```bash
pip install -r requirements.txt
```

## Run

```bash
python -m streamlit run app.py
```

## How to Use

1. Copy [.env.example](.env.example) to [.env](.env).
2. Set `AI_PROVIDER` to the provider you want to use.
3. Fill in the credentials for that provider in [.env](.env).
4. Launch the app.
5. Upload one or more business card images, or use the camera.
6. Start extraction.
7. Review and edit extracted values in the Results tab.
8. Confirm the results.
9. Download JSON or Excel exports if needed.

## Environment Configuration

### Common

```env
AI_PROVIDER=watsonx
```

Supported values:
- `watsonx`
- `openai`
- `azure_openai`
- `gemini`
- `openai_compatible`

### IBM Watsonx

```env
AI_PROVIDER=watsonx
WATSONX_API_KEY=your_api_key
WATSONX_PROJECT_ID=your_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
WATSONX_MODEL_ID=meta-llama/llama-4-maverick-17b-128e-instruct-fp8
```

### OpenAI

```env
AI_PROVIDER=openai
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
```

### Azure OpenAI

```env
AI_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=your_deployment_name
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

### Google Gemini

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=your_api_key
GEMINI_MODEL=gemini-1.5-pro
```

### OpenAI-Compatible On-Prem

```env
AI_PROVIDER=openai_compatible
OPENAI_COMPATIBLE_BASE_URL=http://localhost:11434/v1
OPENAI_COMPATIBLE_API_KEY=
OPENAI_COMPATIBLE_MODEL=llava
```

This mode works for on-prem or private endpoints that expose an OpenAI-compatible chat completions API, such as Ollama gateways or vLLM services.

## Cumulative Storage

Each successful scan is automatically appended to [namecard_results.csv](namecard_results.csv).

CSV columns:
- `Company_Name`
- `Name`
- `Title`
- `Telephone`
- `Direct`
- `Mobile`
- `Fax`
- `Email`
- `Address`
- `Company_Website`
- `Filename`
- `Processing_Timestamp`

## Notes

- The cumulative CSV file is created automatically after the first successful scan.
- Keep [.env](.env) local only. It is already excluded by [.gitignore](.gitignore).
- Share [.env.example](.env.example) instead of sharing your real [.env](.env).
- The active provider is displayed in the sidebar and header of [app.py](app.py).
- Excel export in the UI is optional and separate from cumulative CSV storage.
