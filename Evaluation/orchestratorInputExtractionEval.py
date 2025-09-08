import openai
import os
import pandas as pd
import json
import time
from tqdm import tqdm
from openai import OpenAI
import google.generativeai as genai
import anthropic
from together import Together
from mistralai import Mistral

# Load API keys
os.environ["OPENAI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["TOGETHER_API_KEY"] = ""
os.environ["Mistral_API_KEY"] = ""
model = "mistral-medium-2505"

client = OpenAI()
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
gemini_model = genai.GenerativeModel("gemini-2.5-pro")
claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
together_client = Together()
mistral_client = Mistral(api_key=os.environ["Mistral_API_KEY"])

# Instruction message
SYSTEM_INSTRUCTIONS = {
    "role": "system",
    "content": """
    You are the Orchestrator Agent in a healthcare data-sharing system.
    Your task is to read the user’s request and extract all available details into the required fields.

    For every input you receive, identify the following:

    1- Receiver type — one of: hospital, research lab, insurance company

    2- Receiver country

    3- Sender country

    4- Receiver Ethereum address

    5- Patient Ethereum address

    6- Purpose of sharing — one of: treatment, research, insurance claim, clinical trial, commercial use

    Rules:
    - Extract only what is stated in the user input.
    - If a field is not mentioned, return "missing".
    - Do not guess or infer — you must base your output only on what is written.
    - Ethereum addresses must be copied exactly as written, preserving upper/lowercase letters.
    - Purposes must match one of the allowed categories exactly; if not stated, return "missing".
    - Your output must be a JSON object in this format:
    {
        "receiver_type": "...",
        "receiver_country": "...",
        "sender_country": "...",
        "receiver_eth_address": "...",
        "patient_eth_address": "...",
        "purpose": "..."
    }
    """
}


def call_gpt(prompt: str):
    start = time.time()

    response = client.responses.create(
        model="gpt-4.1",
        instructions=SYSTEM_INSTRUCTIONS["content"],
        input=prompt,
        temperature=0
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

    df["response_time_sec"] = None
    df["raw_response"] = None

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating with Gemini"):
        case = row["case"]
        response, duration = call_gemini(case)

        df.at[idx, "response_time_sec"] = duration
        df.at[idx, "raw_response"] = response

    df.to_csv(output_file, index=False)



def call_claude(prompt: str, temperature: float = 0.0):
    start = time.time()
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            temperature=temperature,
            max_tokens=2000,
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

    df["response_time_sec"] = None
    df["raw_response"] = None

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating with Claude 3.5"):
        case = row["case"]
        response, duration = call_claude(case, temperature=0.0)

        df.at[idx, "response_time_sec"] = duration
        df.at[idx, "raw_response"] = response

    df.to_csv(output_file, index=False)
    print(f"✅ Evaluation complete. Results saved to {output_file}")



def call_together_model(prompt: str, model_name):

    start = time.time()
    
    response = together_client.chat.completions.create(
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
            response, duration = call_together_model(case_text, "deepseek-ai/DeepSeek-V3")
        except Exception as e:
            duration = -1
            response = f"Error: {e}"

        results.append({
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
    
def evaluate_mistral(input_file: str, output_file: str):
    df = pd.read_excel(input_file) if input_file.endswith(".xlsx") else pd.read_csv(input_file)

    if "case" not in df.columns:
        raise ValueError("Input file must contain a column named 'case'.")

    df["response_time_sec"] = None
    df["raw_response"] = None

    for idx, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating with Claude 3.5"):
        case = row["case"]
        response, duration = call_mistral(case)

        df.at[idx, "response_time_sec"] = duration
        df.at[idx, "raw_response"] = response

    df.to_csv(output_file, index=False)
    print(f"✅ Evaluation complete. Results saved to {output_file}")


if __name__ == "__main__":
    INPUT_XLSX = "inputDataset.xlsx"       # Your Excel file
    evaluate_gpt(INPUT_XLSX, "input_results_gpt.csv")
    evaluate_gemini(INPUT_XLSX, "input_results_gemini.csv")
    evaluate_claude(INPUT_XLSX, "input_results_claude.csv")
    evaluate_deepseek(INPUT_XLSX, "input_results_deepseek.csv")
    evaluate_mistral(INPUT_XLSX, "input_results_mistral.csv")
    evaluate_qwen(INPUT_XLSX, "input_results_qwen.csv")
