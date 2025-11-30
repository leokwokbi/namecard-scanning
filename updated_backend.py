import base64
import json
import os
import re
import time
import requests
import pandas as pd
import glob
from dotenv import load_dotenv
from typing import Optional
from pydantic import BaseModel, Field, ValidationError
from PIL import Image
import concurrent.futures
load_dotenv() 

class TimeoutError(Exception):
    pass

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


class NameCardExtractor:
    def __init__(self, image_input_path: str, timeout_seconds: int = 15, 
                 watsonx_api_key: str = None, watsonx_project_id: str = None, 
                 watsonx_url: str = None):
        load_dotenv()
        self.image_input_path = image_input_path
        self.timeout_seconds = timeout_seconds
        
        # Use provided credentials or fallback to environment variables
        self.api_key = watsonx_api_key or os.getenv("WATSONX_API_KEY")
        self.project_id = watsonx_project_id or os.getenv("WATSONX_PROJECT_ID")
        self.watsonx_url = watsonx_url or os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        
        self.api_url = f"{self.watsonx_url}/ml/v1/text/chat?version=2023-05-29"
        self.credentials = {
            "url": self.watsonx_url,
            "apikey": self.api_key
        }
        self.model_id = "meta-llama/llama-4-maverick-17b-128e-instruct-fp8" 
        self.prompt = self._construct_prompt()

    @staticmethod
    def _construct_prompt() -> str:
        return (
            "<|system|> "
            " You are a meticulous and trustworthy AI specializing in extracting business card information from images. Your priority is accuracy and factual correctness. Never assume, estimate, or round off. Extract only explicitly stated values exactly as written. "
            " <|user|> "
            " You are given an image of a name card. Extract the following items: "
            " - Company Name (In cases where the company name is not available on the card, you can derive it from the email's domain. To do this, simply capitalize the first letter of the domain name.)"
            " - Name "
            " - Title "
            " - Tel "
            " - Contact "
            " - Email "
            " Rules: "
            " 1. Extract the exact value as written on the card. Do not infer or guess missing information. "
            " 2. If an item is missing, you have to leave it as '', never mark as 'not found' "
            " 3. DO NOT return markdown formatting (no ```json blocks). Output only valid raw JSON format. "
            " 4. PHONE NUMBER FORMAT: For all phone numbers (Tel, Contact, Mobile, Fax), format them as '+country_code phone_number'. Examples: '+1 9840 4822', '+852 9133 3333', '+86 138 0013 8000'. If country code is not visible on the card, use the most likely country code based on context. If no phone number is found, use 'not found'. "
            " Format your response exactly like this: "
            " { "
            "  \"Company_Name\": \"\",\n"
            "  \"Name\": \"\",\n"
            "  \"Title\": \"\",\n"
            "  \"Telephone\": \"\",\n"
            "  \"Direct\": \"\",\n"
            "  \"Mobile\": \"\",\n"
            "  \"Fax\": \"\",\n"
            "  \"Email\": \"\",\n"
            "  \"Address\": \"\",\n"
            "  \"Company_Website\": \"\"\n"
            " }"
        )

    def encode_image(self) -> str:
        with open(self.image_input_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def get_bearer_token(self) -> str:
        token_url = "https://iam.cloud.ibm.com/identity/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = f"grant_type=urn:ibm:params:oauth:grant-type:apikey&apikey={self.credentials['apikey']}"
        
        try:
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()
            return response.json().get("access_token")
        except requests.exceptions.HTTPError as e:
            if response.status_code == 400:
                raise Exception("Invalid API Key, Project ID or Watsonx URL. Please check your credentials.")
            elif response.status_code == 401:
                raise Exception("Invalid API Key, Project ID or Watsonx URL. Please check your credentials.")
            elif response.status_code == 403:
                raise Exception("Invalid API Key, Project ID or Watsonx URL. Please check your credentials.")
            else:
                raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during authentication: {str(e)}")

    def get_response(self, prompt: str, encoded_image: str, access_token: str) -> str:
        body = {
            "messages": [
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded_image}"}}
                ]}
            ],
            "project_id": self.project_id,
            "model_id": self.model_id,
            "decoding_method": "sample",
            "repetition_penalty": 1.0,
            "temperature": 0,
            "top_p": 0.01,
            "top_k": 1,
            "max_tokens": 4000,
            "random_seed": 1
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=body)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except requests.exceptions.HTTPError as e:
            if response.status_code == 400:
                raise Exception("Invalid API Key, Project ID or Watsonx URL. Please check your credentials.")
            elif response.status_code == 401:
                raise Exception("Invalid API Key, Project ID or Watsonx URL. Please check your credentials.")
            elif response.status_code == 403:
                raise Exception("Invalid API Key, Project ID or Watsonx URL. Please check your credentials.")
            elif response.status_code == 404:
                raise Exception("Invalid API Key, Project ID or Watsonx URL. Please check your credentials.")
            else:
                raise Exception(f"WatsonX API error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Network error during WatsonX request: {str(e)}")

    @staticmethod
    def clean_json_block(text: str) -> str:
        # Remove any accidental markdown formatting
        return re.sub(r"^```json\s*|\s*```$", "", text.strip(), flags=re.DOTALL).strip()

    def process_image(self, index: int, encoded_image: str, prompt: str, token: str) -> tuple[int, str]:
        try:
            filename = os.path.basename(self.image_input_path)
            print(f"🔄 Processing image {filename}")
            text_response = self.get_response(prompt, encoded_image, token)
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
            return index, ""

    def _run_extraction(self) -> str:
        """Internal method to run the actual extraction without timeout"""
        start_time = time.time()
        encoded_image = self.encode_image()
        access_token = self.get_bearer_token()
        index, result = self.process_image(1, encoded_image, self.prompt, access_token)
        print(f"⏱️ Time taken: {time.time() - start_time:.2f} seconds")
        return result

    def run(self) -> str:
        """Run extraction with timeout handling"""
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(self._run_extraction)
                try:
                    result = future.result(timeout=self.timeout_seconds)
                    print(result)
                    return result
                except concurrent.futures.TimeoutError:
                    print(f"❌ Processing timeout after {self.timeout_seconds} seconds")
                    # Return error JSON format
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
                        "Company_Website": ""
                    }
                    return json.dumps(error_result, indent=2)
        except Exception as e:
            print(f"❌ Unexpected error: {str(e)}")
            # Return error JSON format
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
                "Company_Website": ""
            }
            return json.dumps(error_result, indent=2)


if __name__ == "__main__":
    image_folder = "./Sample/"
    # Find both .jpg and .png files
    image_files = glob.glob(os.path.join(image_folder, "*.jpg")) + glob.glob(os.path.join(image_folder, "*.png"))

    results = []
    for idx, image_path in enumerate(image_files, 1):
        print(f"\n🖼️ Processing image {idx}/{len(image_files)}: {os.path.basename(image_path)}")
        extractor = NameCardExtractor(image_input_path=image_path, timeout_seconds=15)
        result = extractor.run()
        results.append({"image": os.path.basename(image_path), "data": result})

    # Save results to a JSON file
    with open("namecard_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Batch processing complete! Results saved to namecard_results.json")


## Phone Number Normalization Function
def normalize_phone(number: str) -> str:
    if not number or not isinstance(number, str):
        return ""
    number = number.strip()
    # Convert (country code) to +countrycode
    number = re.sub(r'^\((\d{1,4})\)', r'+\1', number)
    # Convert '00' at start to '+'
    number = re.sub(r'^00', '+', number)
    # Remove all non-digit except leading '+'
    number = re.sub(r'[^\d+]', '', number)
    # Remove duplicate pluses
    number = re.sub(r'^\++', '+', number)
    # Now, extract country code (1-4 digits) and the rest
    match = re.match(r'^(\+\d{1,4})(\d+)$', number)
    if match:
        country = match.group(1)
        local = match.group(2)
        return f"{country} {local}"
    # If no country code, just return digits
    return number


def export_results_to_excel():
    """Export results to Excel - only run when called explicitly"""
    # Export results to Excel
    # Load the results from the JSON file
    try:
        with open("namecard_results.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract only the data part for each image
        records = []
        for item in data:
            # If result is a string, parse it as JSON
            if isinstance(item["data"], str):
                record = json.loads(item["data"])
            else:
                record = item["data"]
            records.append(record)

        # Create DataFrame with the specified column order
        df = pd.DataFrame(records, columns=[
            "Company_Name", "Name", "Title", "Telephone", "Direct", "Mobile", "Fax", "Email", "Address", "Company_Website"
        ])

        # Save to Excel
        df.to_excel("namecard_results.xlsx", index=False)
        print("✅ Results exported to namecard_results.xlsx")
        
    except FileNotFoundError:
        print("❌ namecard_results.json not found. Please run the batch processing first.")
    except Exception as e:
        print(f"❌ Error exporting to Excel: {str(e)}")


# Only run the export function when this script is executed directly
if __name__ == "__main__":
    # Also call the export function after batch processing
    export_results_to_excel()