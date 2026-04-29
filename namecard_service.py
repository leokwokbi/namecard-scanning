import base64
import concurrent.futures
import glob
import json
import os
import re
import time
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

RESULT_COLUMNS = [
    "Company_Name",
    "Name",
    "Title",
    "Telephone",
    "Direct",
    "Mobile",
    "Fax",
    "Email",
    "Address",
    "Company_Website",
]
RESULTS_JSON_PATH = Path("namecard_results.json")
RESULTS_CSV_PATH = Path("namecard_results.csv")


class NameCardOutput(BaseModel):
    Company_Name: Optional[str] = Field(default="")
    Name: Optional[str] = Field(default="")
    Title: Optional[str] = Field(default="")
    Telephone: Optional[str] = Field(default="")
    Direct: Optional[str] = Field(default="")
    Mobile: Optional[str] = Field(default="")
    Fax: Optional[str] = Field(default="")
    Email: Optional[str] = Field(default="")
    Address: Optional[str] = Field(default="")
    Company_Website: Optional[str] = Field(default="")


class BaseProvider:
    def __init__(self, model_id: str):
        self.model_id = model_id

    def extract(self, prompt: str, encoded_image: str) -> str:
        raise NotImplementedError


class WatsonxProvider(BaseProvider):
    def __init__(self):
        self.api_key = os.getenv("WATSONX_API_KEY", "")
        self.project_id = os.getenv("WATSONX_PROJECT_ID", "")
        self.base_url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        model_id = os.getenv("WATSONX_MODEL_ID", "meta-llama/llama-4-maverick-17b-128e-instruct-fp8")
        super().__init__(model_id=model_id)
        self.api_url = f"{self.base_url}/ml/v1/text/chat?version=2023-05-29"

    def get_bearer_token(self) -> str:
        if not self.api_key or not self.project_id:
            raise Exception("Missing Watsonx credentials in .env")

        token_url = "https://iam.cloud.ibm.com/identity/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={self.api_key}"

        try:
            response = requests.post(token_url, headers=headers, data=data, timeout=30)
            response.raise_for_status()
            token = response.json().get("access_token", "")
            if not token:
                raise Exception("Watsonx access token was empty")
            return token
        except requests.exceptions.HTTPError as e:
            response = e.response
            if response is not None and response.status_code in {400, 401, 403}:
                raise Exception("Invalid Watsonx credentials or URL.")
            if response is not None:
                raise Exception(f"Watsonx authentication failed: {response.status_code} - {response.text}")
            raise Exception(f"Watsonx authentication failed: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during Watsonx authentication: {str(e)}")

    def extract(self, prompt: str, encoded_image: str) -> str:
        access_token = self.get_bearer_token()
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}},
                    ],
                }
            ],
            "project_id": self.project_id,
            "model_id": self.model_id,
            "decoding_method": "sample",
            "repetition_penalty": 1.0,
            "temperature": 0,
            "top_p": 0.01,
            "top_k": 1,
            "max_tokens": 4000,
            "random_seed": 1,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}",
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=body, timeout=90)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            response = e.response
            if response is not None and response.status_code in {400, 401, 403, 404}:
                raise Exception("Invalid Watsonx request, credentials, project, or URL.")
            if response is not None:
                raise Exception(f"Watsonx API error: {response.status_code} - {response.text}")
            raise Exception(f"Watsonx API error: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during Watsonx request: {str(e)}")


class OpenAICompatibleProvider(BaseProvider):
    def __init__(self, base_url_env: str, api_key_env: str, model_env: str, provider_name: str, default_base_url: str = ""):
        self.provider_name = provider_name
        self.base_url = os.getenv(base_url_env, default_base_url).rstrip("/")
        self.api_key = os.getenv(api_key_env, "")
        model_id = os.getenv(model_env, "")
        super().__init__(model_id=model_id)

    def extract(self, prompt: str, encoded_image: str) -> str:
        if not self.base_url:
            raise Exception(f"Missing {self.provider_name} base URL in .env")
        if not self.model_id:
            raise Exception(f"Missing {self.provider_name} model in .env")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body = {
            "model": self.model_id,
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}},
                    ],
                }
            ],
        }

        try:
            response = requests.post(f"{self.base_url}/chat/completions", headers=headers, json=body, timeout=90)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            response = e.response
            if response is not None:
                raise Exception(f"{self.provider_name} API error: {response.status_code} - {response.text}")
            raise Exception(f"{self.provider_name} API error: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during {self.provider_name} request: {str(e)}")


class AzureOpenAIProvider(BaseProvider):
    def __init__(self):
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        self.deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        super().__init__(model_id=self.deployment)

    def extract(self, prompt: str, encoded_image: str) -> str:
        if not self.api_key or not self.endpoint or not self.deployment:
            raise Exception("Missing Azure OpenAI configuration in .env")

        url = (
            f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions"
            f"?api-version={self.api_version}"
        )
        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }
        body = {
            "temperature": 0,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}},
                    ],
                }
            ],
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=90)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            response = e.response
            if response is not None:
                raise Exception(f"Azure OpenAI API error: {response.status_code} - {response.text}")
            raise Exception(f"Azure OpenAI API error: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during Azure OpenAI request: {str(e)}")


class GeminiProvider(BaseProvider):
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY", "")
        model_id = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
        super().__init__(model_id=model_id)

    def extract(self, prompt: str, encoded_image: str) -> str:
        if not self.api_key or not self.model_id:
            raise Exception("Missing Gemini configuration in .env")

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_id}:generateContent?key={self.api_key}"
        )
        headers = {"Content-Type": "application/json"}
        body = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": encoded_image,
                            }
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0,
            },
        }

        try:
            response = requests.post(url, headers=headers, json=body, timeout=90)
            response.raise_for_status()
            payload = response.json()
            return payload["candidates"][0]["content"]["parts"][0]["text"]
        except requests.exceptions.HTTPError as e:
            response = e.response
            if response is not None:
                raise Exception(f"Gemini API error: {response.status_code} - {response.text}")
            raise Exception(f"Gemini API error: {str(e)}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during Gemini request: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected Gemini response format: {str(e)}")


class NameCardExtractor:
    def __init__(self, image_input_path: str, timeout_seconds: int = 15):
        load_dotenv()
        self.image_input_path = image_input_path
        self.timeout_seconds = timeout_seconds
        self.provider_name = os.getenv("AI_PROVIDER", "watsonx").strip().lower()
        self.prompt = self._construct_prompt()
        self.provider = self._build_provider()

    def _build_provider(self) -> BaseProvider:
        if self.provider_name == "watsonx":
            return WatsonxProvider()
        if self.provider_name == "openai":
            return OpenAICompatibleProvider(
                base_url_env="OPENAI_BASE_URL",
                api_key_env="OPENAI_API_KEY",
                model_env="OPENAI_MODEL",
                provider_name="OpenAI",
                default_base_url="https://api.openai.com/v1",
            )
        if self.provider_name == "azure_openai":
            return AzureOpenAIProvider()
        if self.provider_name == "gemini":
            return GeminiProvider()
        if self.provider_name == "openai_compatible":
            return OpenAICompatibleProvider(
                base_url_env="OPENAI_COMPATIBLE_BASE_URL",
                api_key_env="OPENAI_COMPATIBLE_API_KEY",
                model_env="OPENAI_COMPATIBLE_MODEL",
                provider_name="OpenAI-compatible provider",
            )
        raise Exception(
            "Unsupported AI_PROVIDER. Use watsonx, openai, azure_openai, gemini, or openai_compatible."
        )

    @staticmethod
    def _construct_prompt() -> str:
        return (
            "You are a meticulous and trustworthy AI specializing in extracting business card information from images. "
            "Your priority is accuracy and factual correctness. Never assume, estimate, or round off. "
            "Extract only explicitly stated values exactly as written.\n\n"
            "You are given an image of a name card. Extract the following items:\n"
            "- Company Name\n"
            "- Name\n"
            "- Title\n"
            "- Telephone\n"
            "- Direct\n"
            "- Mobile\n"
            "- Fax\n"
            "- Email\n"
            "- Address\n"
            "- Company Website\n\n"
            "Rules:\n"
            "1. Extract the exact value as written on the card. Do not infer or guess missing information.\n"
            "2. If an item is missing, leave it as an empty string.\n"
            "3. Return only valid raw JSON. Do not use markdown fences.\n"
            "4. If the company name is not explicitly shown but can be safely derived from the email domain, use it.\n"
            "5. Preserve phone numbers as written unless minor whitespace normalization is needed.\n\n"
            "Return exactly this JSON structure:\n"
            "{\n"
            '  "Company_Name": "",\n'
            '  "Name": "",\n'
            '  "Title": "",\n'
            '  "Telephone": "",\n'
            '  "Direct": "",\n'
            '  "Mobile": "",\n'
            '  "Fax": "",\n'
            '  "Email": "",\n'
            '  "Address": "",\n'
            '  "Company_Website": ""\n'
            "}"
        )

    def encode_image(self) -> str:
        with open(self.image_input_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    @staticmethod
    def clean_json_block(text: str) -> str:
        return re.sub(r"^```json\s*|\s*```$", "", text.strip(), flags=re.DOTALL).strip()

    def process_image(self, index: int, encoded_image: str, prompt: str) -> tuple[int, str]:
        try:
            filename = os.path.basename(self.image_input_path)
            print(f"🔄 Processing image {filename} with provider {self.provider_name}")
            text_response = self.provider.extract(prompt, encoded_image)
            cleaned_text = self.clean_json_block(text_response)
            parsed_dict = json.loads(cleaned_text)

            try:
                validated = NameCardOutput.model_validate(parsed_dict)
                print(f"✅ Validation successful for image {index}")
                validated_output = validated.model_dump_json(indent=2)
            except ValidationError as e:
                print(f"⚠️ Validation failed for image {index}: {e}")
                validated_output = json.dumps(parsed_dict, indent=2)

            return index, validated_output
        except Exception as e:
            print(f"❌ Error processing image {index}: {e}")
            return index, json.dumps({"error": str(e)})

    def _run_extraction(self) -> str:
        start_time = time.time()
        encoded_image = self.encode_image()
        _, result = self.process_image(1, encoded_image, self.prompt)
        print(f"⏱️ Time taken: {time.time() - start_time:.2f} seconds")
        return result

    def run(self) -> str:
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._run_extraction)
                try:
                    result = future.result(timeout=self.timeout_seconds)
                    print(result)
                    return result
                except concurrent.futures.TimeoutError:
                    print(f"❌ Processing timeout after {self.timeout_seconds} seconds")
                    error_result = {
                        "error": f"Processing timeout after {self.timeout_seconds} seconds",
                        "Company_Name": "",
                        "Name": "",
                        "Title": "",
                        "Telephone": "",
                        "Direct": "",
                        "Mobile": "",
                        "Fax": "",
                        "Email": "",
                        "Address": "",
                        "Company_Website": "",
                    }
                    return json.dumps(error_result, indent=2)
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            error_result = {
                "error": f"Processing failed: {str(e)}",
                "Company_Name": "",
                "Name": "",
                "Title": "",
                "Telephone": "",
                "Direct": "",
                "Mobile": "",
                "Fax": "",
                "Email": "",
                "Address": "",
                "Company_Website": "",
            }
            return json.dumps(error_result, indent=2)


def normalize_phone(number: str) -> str:
    if not number or not isinstance(number, str):
        return ""
    number = number.strip()
    number = re.sub(r"^\((\d{1,4})\)", r"+\1", number)
    number = re.sub(r"^00", "+", number)
    number = re.sub(r"[^\d+]", "", number)
    number = re.sub(r"^\++", "+", number)
    match = re.match(r"^(\+\d{1,4})(\d+)$", number)
    if match:
        country = match.group(1)
        local = match.group(2)
        return f"{country} {local}"
    return number


def result_has_data(record: dict) -> bool:
    return any(str(record.get(column, "")).strip() for column in RESULT_COLUMNS)


def build_result_record(data: dict, filename: str = "", timestamp: str = "") -> dict:
    normalized = {column: str(data.get(column, "") or "").strip() for column in RESULT_COLUMNS}
    normalized["Filename"] = filename
    normalized["Processing_Timestamp"] = timestamp
    return normalized


def append_results_to_csv(results, csv_path: Path = RESULTS_CSV_PATH) -> int:
    records = []

    for result in results:
        if result.get("status") != "success" or "data" not in result:
            continue

        record = build_result_record(
            result["data"],
            filename=result.get("filename", ""),
            timestamp=result.get("timestamp", ""),
        )

        if result_has_data(record):
            records.append(record)

    if not records:
        return 0

    new_df = pd.DataFrame(records)
    ordered_columns = RESULT_COLUMNS + ["Filename", "Processing_Timestamp"]
    new_df = new_df[ordered_columns]

    if csv_path.exists():
        existing_df = pd.read_csv(csv_path)
        for column in ordered_columns:
            if column not in existing_df.columns:
                existing_df[column] = ""
        existing_df = existing_df[ordered_columns]
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    combined_df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    return len(records)


def export_results_to_csv():
    """Export results to CSV from JSON results file."""
    try:
        with open(RESULTS_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        csv_ready_results = []
        for item in data:
            record_data = json.loads(item["data"]) if isinstance(item["data"], str) else item["data"]
            csv_ready_results.append(
                {
                    "status": "success",
                    "filename": item.get("image", ""),
                    "timestamp": "",
                    "data": record_data,
                }
            )

        appended_count = append_results_to_csv(csv_ready_results, RESULTS_CSV_PATH)
        print(f"✅ {appended_count} records saved to {RESULTS_CSV_PATH}")
    except FileNotFoundError:
        print(f"❌ {RESULTS_JSON_PATH} not found. Please run the batch processing first.")
    except Exception as e:
        print(f"❌ Error exporting to CSV: {str(e)}")


if __name__ == "__main__":
    image_folder = "./Sample/"
    image_files = glob.glob(os.path.join(image_folder, "*.jpg")) + glob.glob(os.path.join(image_folder, "*.png"))

    results = []
    for idx, image_path in enumerate(image_files, 1):
        print(f"\n🖼️ Processing image {idx}/{len(image_files)}: {os.path.basename(image_path)}")
        extractor = NameCardExtractor(image_input_path=image_path, timeout_seconds=15)
        result = extractor.run()
        results.append({"image": os.path.basename(image_path), "data": result})

    with open(RESULTS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Batch processing complete! Results saved to {RESULTS_JSON_PATH}")
    export_results_to_csv()

# Made with Bob
