import time
import pandas as pd
from tqdm import tqdm
from together import Together
import os
import ast
from mistralai import Mistral

# Set Together API key
os.environ["TOGETHER_API_KEY"] = ""
client = Together()
mistral_api_key = ""
mistral_client = Mistral(api_key=mistral_api_key)

# Data Filtering Agent Instruction
SYSTEM_INSTRUCTIONS = {
    "role": "system",
    "content": """
        You are a Data Filtering Agent responsible for preparing free-text patient records for compliant cross-border healthcare data sharing. Your job is to strictly follow the data sharing policy to filter and anonymize each patient file.

        You will receive:
        1. A patient file in natural language.
        2. A sharing policy with:
            - `allowed data types`: list of allowed data types.
            - `anonymization required`: true or false.

        Your task is to:
        1. Read and understand the patient file.
        2. Keep only information that belongs to the allowed data types.
        3. Remove any information related to disallowed data types.
        4. If anonymization is required, anonymize all personally identifiable information (PII) as described below.

        ----------------------------------------
        DATA TYPES TO FILTER:
        ----------------------------------------
        This is the full  list of data types considered. Only retain content matching any of the following allowed types:

        1. Clinical Notes & Diagnosis
            - Examples: presenting complaints, clinical impressions, physician notes, diagnoses, medications.

        2. Lab & Test Results
            - Examples: blood test results, hormone levels, imaging reports, ECG, biopsy.

        3. Genomic Data
            - Examples: genetic test results, gene mutations, inherited disorder risk.

        4. Mental Health Data
            - Examples: mood assessments, psychiatric notes, therapy records, depression scores.

        5. PHRs (e.g. Device Records)
            - Examples: wearable data (Fitbit, Apple Watch), home device logs, self-tracking.

        6. Medical History
            - Examples: past illnesses, surgical history, allergies, family disease history.

        FILTERING RULES
        - Include only the content that falls under the allowed data types.
        - Remove entirely any sentences, phrases, or sections containing non-allowed types.
        - If a paragraph contains mixed content, extract and keep only the portions related to allowed types.
        - Do not summarize or rephrase unrelated data types — just remove them.

        ----------------------------------------
        ANONYMIZATION RULES:
        ----------------------------------------
        If `anonymization_required` is true, apply the following rules:

        - Remove all PII
        - You may rewrite some information to retain its clinical value without identifying the patient. For example:
            "DOB: 1989-03-21" → "36-year-old"
        - Dates of visit/labs → DO NOT remove (they should always be preserved)

        If `anonymization_required` is false, retain all original PII.

        ----------------------------------------
        OUTPUT FORMAT:
        ----------------------------------------
        - Return only the cleaned and filtered patient file.
        - Keep the original file format and structure just remove/replace unwanted data.
        - Do not include any JSON, markdown, or explanations.
        - Keep it natural and readable, as if written by a clinician.
        - No extra notes, just the compliant version of the patient record.
        - Important: Don't return the thinking process details, just the filtered file text!!!!
    """
}

def call_together_model(prompt: str, model_name):
    start = time.time()
    
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            SYSTEM_INSTRUCTIONS["content"],
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )

    end = time.time()
    return response.choices[0].message.content, round(end - start, 2)



def evaluate(input_xlsx: str, output_csv: str, model_name):
    df = pd.read_excel(input_xlsx, sheet_name="Sheet1")

    if not {"Case", "File", "Allowed Data Types", "Anonymization Required"}.issubset(df.columns):
        raise ValueError("Excel file must contain columns: 'Case', 'File', 'Allowed Data Types', 'Anonymization Required'")

    results = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating Data Filtering Agent"):
        case_id = row["Case"]
        file_text = str(row["File"]).strip()
        try:
            allowed = ast.literal_eval(row["Allowed Data Types"]) if isinstance(row["Allowed Data Types"], str) else row["Allowed Data Types"]
        except Exception:
            allowed = []

        anonymize = bool(row["Anonymization Required"])

        user_prompt = f"""
        Patient File:
        {file_text}

        Allowed Data Types: {allowed}
        Anonymization Required: {anonymize}
        """

        try:
            response, duration = call_together_model(user_prompt, model_name)
        except Exception as e:
            response = f"ERROR: {e}"
            duration = -1

        results.append({
            "Case": case_id,
            "response_time_sec": duration,
            "raw_response": response
        })

    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Results written to {output_csv}")



def call_mistral(prompt: str):
    start = time.time()

    try:
        response = client.chat.complete(
            model="mistral-medium-2505",
            messages=[
                SYSTEM_INSTRUCTIONS["content"],
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=2048,
        )
        content = response.choices[0].message.content
        duration = round(time.time() - start, 2)
        return content, duration
    except Exception as e:
        return f"ERROR: {e}", -1

def evaluate_mistral(input_xlsx: str, output_csv: str, sheet_name="Sheet1"):
    df = pd.read_excel(input_xlsx, sheet_name=sheet_name)

    required_cols = {"Case", "File", "Allowed Data Types", "Anonymization Required"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"Input file must contain columns: {required_cols}")

    results = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating Mistral-Medium"):
        case_id = row["Case"]
        file_text = str(row["File"]).strip()

        try:
            allowed = ast.literal_eval(row["Allowed Data Types"]) if isinstance(row["Allowed Data Types"], str) else row["Allowed Data Types"]
        except Exception:
            allowed = []

        anonymize = bool(row["Anonymization Required"])

        user_prompt = f"""Patient File:
        {file_text}

        Allowed Data Types: {allowed}
        Anonymization Required: {anonymize}"""

        response_text, duration = call_mistral(user_prompt)

        results.append({
            "Case": case_id,
            "response_time_sec": duration,
            "filtered_file": response_text
        })

    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Results saved to {output_csv}")



# Reflection Agent Instruction (updated system instructions)
SYSTEM_INSTRUCTIONS2 = {
    "role": "system",
    "content": """
You are a Data Filtering Agent responsible for preparing free-text patient records for compliant cross-border healthcare data sharing. Your job is to strictly follow the data sharing policy to filter and anonymize each patient file. 
Specifically, you are a reflection agent responsible for verifying and correcting a previously filtered patient file.

You will receive:
1. The original patient file.
2. A previously filtered output.
3. A list of allowed data types.
4. An anonymization requirement. (true or false)

Your task is to:
- Compare the original file with the filtered output.
- Reinsert any allowed data that was mistakenly removed.
- Remove any disallowed data that was mistakenly retained.
- Ensure that if anonymization is required, all PII is removed or rewritten appropriately.
- Location and physician are considered PII!
- If anonymization is not required, all original PII should be retained.

This is the full list of data types considered. Only retain content matching any of the following allowed types:

    1. Clinical Notes & Diagnosis
        - Examples: presenting complaints, clinical impressions, physician notes, diagnoses, medications, ordered tests, treatment plan, and follow up.

    2. Lab & Test Results
        - Examples: blood test results, hormone levels, imaging reports, ECG, biopsy.

    3. Genomic Data
        - Examples: genetic test results, gene mutations, inherited disorder risk.

    4. Mental Health Data
        - Examples: mood assessments, psychiatric notes, therapy records, depression scores.

    5. PHRs (e.g. Device Records)
        - Examples: wearable data (Fitbit, Apple Watch), home device logs, self-tracking.

    6. Medical History
        - Examples: past illnesses, surgical history, allergies, family disease history.

    FILTERING RULES
    - Include only the content that falls under the allowed data types.
    - Always pay attention to the "clinical Notes & Diagnosis" category as it includes many fields!!
    - Medications are always considered part of the "clinical Notes & Diagnosis" category!!
    - Always keep age and date of file!!
    - Remove entirely any sentences, phrases, or sections containing non-allowed types.
    - If a paragraph contains mixed content, extract and keep only the portions related to allowed types.
    - Do not summarize or rephrase unrelated data types — just remove them.

⚠️ Do not include any reasoning or explanation.
⚠️ Only return the corrected patient file in natural original format.
"""
}

def call_qwen_reflection(prompt: str):
    start = time.time()

    response = client.chat.completions.create(
        model="Qwen/Qwen3-235B-A22B-fp8-tput",
        messages=[
            SYSTEM_INSTRUCTIONS2["content"],
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )

    end = time.time()
    return response.choices[0].message.content, round(end - start, 2)

def evaluate_reflection(input_xlsx: str, output_csv: str, sheet_name="Sheet1"):
    df = pd.read_excel(input_xlsx, sheet_name=sheet_name)

    required_columns = {"File", "Filtered File", "Allowed Data Types", "Anonymization Required"}
    if not required_columns.issubset(df.columns):
        raise ValueError(f"Excel file must contain columns: {required_columns}")

    results = []

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Running Reflection Agent"):
        try:
            original_file = str(row["File"]).strip()
            filtered_file = str(row["Filtered File"]).strip()
            allowed = ast.literal_eval(row["Allowed Data Types"]) if isinstance(row["Allowed Data Types"], str) else row["Allowed Data Types"]
            anonymize = bool(row["Anonymization Required"])
        except Exception as e:
            results.append({
                "Case": idx,
                "error": f"Input parsing error: {e}",
                "corrected_output": ""
            })
            continue

        user_prompt = f"""--- Original Patient File ---
{original_file}

--- Previous Filtered Output ---
{filtered_file}

--- Allowed Data Types ---
{allowed}

--- Anonymization Required ---
{anonymize}"""

        try:
            corrected_output, duration = call_qwen_reflection(user_prompt)
        except Exception as e:
            corrected_output = f"ERROR: {e}"
            duration = -1

        results.append({
            "Case": idx,
            "response_time_sec": duration,
            "corrected_output": corrected_output
        })

    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Reflected results saved to {output_csv}")
    


if __name__ == "__main__":
    INPUT_XLSX = "filteringDataset.xlsx"         # Your Excel file
    evaluate(INPUT_XLSX, "filtering_results_deepseek.csv", "deepseek-ai/DeepSeek-V3")
    evaluate(INPUT_XLSX, "filtering_results_gemma.csv", "google/gemma-2-27b-it")
    evaluate(INPUT_XLSX, "filtering_results_llama.csv", "meta-llama/Llama-4-Maverick-17B-128E-Instruct-FP8")
    evaluate_mistral(INPUT_XLSX, "filtering_results_mistral.csv")
    evaluate(INPUT_XLSX, "filtering_results_qwen.csv", "Qwen/Qwen3-235B-A22B-fp8-tput")
    INPUT_XLSX2 = "reflectionFilteringDataset.xlsx"
    evaluate_reflection(INPUT_XLSX2, "filtering_results_qwen_with_reflection.csv")
