import os
import pandas as pd
import time
import json
from tqdm import tqdm
from openai import OpenAI
import google.generativeai as genai
import anthropic
from together import Together

# Load API keys
os.environ["OPENAI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["TOGETHER_API_KEY"] = ""

client = OpenAI()
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
gemini_model = genai.GenerativeModel("gemini-2.5-pro")
claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
client = Together()

# Instruction message (GPT system prompt)
SYSTEM_INSTRUCTIONS = {
    "role": "system",
    "content": (
        "You are a healthcare consent validation assistant.\n"
        "You will be given a data sharing request and a list of available consents.\n"
        "Your job is to determine if valid consent exists that satisfies the regulatory requirements for sharing the requested data.\n"
        "If valid consent(s) exist, return a list of all allowed data types covered by *every* applicable valid consent — not just one.\n\n"
        "You must evaluate **all types of consents** carefully:\n"
        "1. **Specific Consent**: Match by receiver Ethereum address, requested purpose, and ensure it is active.\n"
        "2. **Hospital/Research Lab/Insurance Consents**: This is based on the receiver role. Match the country, requested purpose, and ensure the consent is active.\n"
        "3. **Universal Consent**: This is valid for all receiver roles. Match receiver country and requested purpose, and ensure the consent is active.\n"
        "4. **Government Consent**: Check only if explicitly required in the regulation requirements. If required, an active government consent for the requested purpose must exist.\n\n"
        "The sharing is considered valid if **at least one** valid patient consent exists that satisfies the required consent type, and **government consent is present if required**.\n\n"
        "⚠️ Important: You must review *ALL* consents that are available and check all the one applies and merge all allowed data types from all valid matches.\n\n"
        "You have to check all the consents and at the end combine all the allowed data types from all valid consents!\n"
        "⚠️ Important: If government consent is required, then the final allowed data types must be the intersection of what is approved by both the patient and the government!!\n"
        "Respond only in this exact JSON format without any explanation:\n"
        "{\n"
        "  \"valid\": true or false,\n"
        "  \"allowed_data_types\": [\"...\"]  // Include only if valid is true\n"
        "}\n\n"
        "The full list of available data types is:\n"
        "['Clinical Notes & Diagnosis', 'Lab & Test Results', 'Genomic Data', 'Mental Health Data', 'PHRs (e.g. Device Records)', 'All Data Types']\n"
    )
}


def parse_response(text: str):
    try:
        cleaned = text.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(cleaned)
        valid = parsed.get("valid", None)
        allowed = parsed.get("allowed_data_types", [])
        return valid, allowed
    except Exception:
        return None, []


def call_gpt(prompt: str):
    start = time.time()

    response = client.responses.create(
        model="gpt-4.1",
        instructions=SYSTEM_INSTRUCTIONS["content"],
        input=prompt,
        #temperature=0
    )

    end = time.time()
    elapsed = round(end - start, 2)

    message = response.output_text

    return message, elapsed

def evaluate_gpt(input_xlsx: str, output_csv: str, sheet_name="Sheet1"):
    df = pd.read_excel(input_xlsx, sheet_name=sheet_name)
    if "case" not in df.columns:
        raise ValueError("Input Excel file must contain a column named 'case'.")

    results = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating GPT"):
        case_text = row["case"]
        try:
            response, duration = call_gpt(case_text)
        except Exception as e:
            duration = -1
            response = f"Error: {e}"

        results.append({
            "id": row.get("id", idx),
            "response_time_sec": duration,
            "raw_response": response
        })

    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Results written to {output_csv}")



def call_gemini(prompt: str):
    full_prompt = SYSTEM_INSTRUCTIONS["content"] + "\n\n" + prompt
    start = time.time()

    try:
        response = gemini_model.generate_content(
            full_prompt,
            generation_config={
                "temperature": 0.0
            }
        )
        end = time.time()
        duration = round(end - start, 2)
        return response.text.strip(), duration
    except Exception as e:
        return f"Error: {e}", -1

def evaluate_gemini(input_file: str, output_file: str):
    df = pd.read_excel(input_file) if input_file.endswith(".xlsx") else pd.read_csv(input_file)

    if "case" not in df.columns:
        raise ValueError("Input file must contain a column named 'case'.")

    df["valid_extracted"] = None
    df["allowed_types_extracted"] = None
    df["response_time_sec"] = None
    df["raw_response"] = None

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating with Gemini"):
        case = row["case"]
        response, duration = call_gemini(case)
        valid, allowed = parse_response(response)

        df.at[idx, "valid_extracted"] = valid
        df.at[idx, "allowed_types_extracted"] = allowed
        df.at[idx, "response_time_sec"] = duration
        df.at[idx, "raw_response"] = response

    df.to_csv(output_file, index=False)
    print(f"✅ Evaluation complete. Results saved to {output_file}")



def call_claude(prompt: str, temperature: float = 0.0):
    start = time.time()
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            temperature=temperature,
            max_tokens=1024,
            system=SYSTEM_INSTRUCTIONS["content"],
            messages=[{"role": "user", "content": prompt}]
        )
        end = time.time()
        duration = round(end - start, 2)
        return message.content[0].text.strip(), duration
    except Exception as e:
        return f"Error: {e}", -1

def evaluate_claude(input_file: str, output_file: str):
    df = pd.read_excel(input_file) if input_file.endswith(".xlsx") else pd.read_csv(input_file)

    if "case" not in df.columns:
        raise ValueError("Input file must contain a column named 'case'.")

    df["valid_extracted"] = None
    df["allowed_types_extracted"] = None
    df["response_time_sec"] = None
    df["raw_response"] = None

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating with Claude 3.5"):
        case = row["case"]
        response, duration = call_claude(case, temperature=0.0)
        valid, allowed = parse_response(response)

        df.at[idx, "valid_extracted"] = valid
        df.at[idx, "allowed_types_extracted"] = allowed
        df.at[idx, "response_time_sec"] = duration
        df.at[idx, "raw_response"] = response

    df.to_csv(output_file, index=False)
    print(f"✅ Evaluation complete. Results saved to {output_file}")



def call_together_model(prompt: str, model_name):

    start = time.time()
    
    response = client.chat.completions.create(
        model=model_name,
        messages= [
            SYSTEM_INSTRUCTIONS["content"],
            {"role": "user", "content": prompt}
        ],
        temperature= 0.0
    )

    end = time.time()
    elapsed = round(end - start, 2)

    message = response.choices[0].message.content

    return message, elapsed



def evaluate_deepseek(input_xlsx: str, output_csv: str, sheet_name="Sheet1"):
    df = pd.read_excel(input_xlsx, sheet_name=sheet_name)
    if "case" not in df.columns:
        raise ValueError("Input Excel file must contain a column named 'case'.")

    results = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating GPT"):
        case_text = row["case"]
        try:
            response, duration = call_together_model(case_text, "deepseek-ai/DeepSeek-V1")
        except Exception as e:
            duration = -1
            response = f"Error: {e}"

        results.append({
            "id": row.get("id", idx),
            "response_time_sec": duration,
            "raw_response": response
        })

    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Results written to {output_csv}")



def evaluate_mistral(input_xlsx: str, output_csv: str, sheet_name="Sheet1"):
    df = pd.read_excel(input_xlsx, sheet_name=sheet_name)
    if "case" not in df.columns:
        raise ValueError("Input Excel file must contain a column named 'case'.")

    results = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating GPT"):
        case_text = row["case"]
        try:
            response, duration = call_together_model(case_text, "mistralai/Mistral-7B-Instruct-v0.3")
        except Exception as e:
            duration = -1
            response = f"Error: {e}"

        results.append({
            "id": row.get("id", idx),
            "response_time_sec": duration,
            "raw_response": response
        })

    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Results written to {output_csv}")



def evaluate_qwen(input_xlsx: str, output_csv: str, sheet_name="Sheet1"):
    df = pd.read_excel(input_xlsx, sheet_name=sheet_name)
    if "case" not in df.columns:
        raise ValueError("Input Excel file must contain a column named 'case'.")

    results = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating GPT"):
        case_text = row["case"]
        try:
            response, duration = call_together_model(case_text, "Qwen/Qwen3-235B-A22B-fp8-tput")
        except Exception as e:
            duration = -1
            response = f"Error: {e}"

        results.append({
            "id": row.get("id", idx),
            "response_time_sec": duration,
            "raw_response": response
        })

    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Results written to {output_csv}")


if __name__ == "__main__":
    INPUT_XLSX = "consentDataset.xlsx"
    evaluate_gpt(INPUT_XLSX, "consent_results_gpt.csv")
    evaluate_gemini(INPUT_XLSX, "consent_results_gemini.csv")
    evaluate_claude(INPUT_XLSX, "consent_results_claude.csv")
    evaluate_deepseek(INPUT_XLSX, "consent_results_deepseek.csv")
    evaluate_mistral(INPUT_XLSX, "consent_results_mistral.csv")
    evaluate_qwen(INPUT_XLSX, "consent_results_qwen.csv")