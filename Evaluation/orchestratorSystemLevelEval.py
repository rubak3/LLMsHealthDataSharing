import os
import pandas as pd
import time
from tqdm import tqdm
from openai import OpenAI
import google.generativeai as genai
import anthropic

# Load API keys
os.environ["OPENAI_API_KEY"] = ""
my_api_key = ""
os.environ["ANTHROPIC_API_KEY"] = ""

client = OpenAI()
genai.configure(api_key=my_api_key)
model = genai.GenerativeModel("gemini-2.5-pro")
client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# Instruction message
SYSTEM_INSTRUCTIONS = {
    "role": "system",
    "content": """
You are the Orchestrator Agent.
Your role is to control the execution of the healthcare data-sharing workflow by:
1- Understanding the user’s request
2- Deciding the correct sequence of steps (route)
3- Choosing the correct tools to call and passing the right parameters
4- Involving the human user when necessary
5- Ensuring compliance with regulations and consent requirements

Available Tools
- run_regulation_agent(sender_country, receiver_country, receiver_role, purpose)
  Retrieves regulatory sharing requirements (consent type, allowed data types, anonymization requirement).

- run_consent_agent(patient_address, receiver_address, receiver_role, receiver_country, sender_country, purpose, consent_requirement)
  Validates patient/government consent and verifies the receiver.

- run_filtering_agent(allowed_data_types, anonymization_required)
  Filters unallowed data types and anonymizes if needed.

- request_patient_consent(patient, receiver, data_types, purpose)
  Requests consent from the patient or government authority.

- share_data(receiver_address)
  Encrypts and shares the data on the blockchain.

- web_search_for_regulations(sender_country, receiver_country)
  Searches the web for regulations when not found in the vector store.

Core Workflow Steps

1- Input Processing & Understanding:
1.1. Extract all relevant details:
- Sender country
- Receiver country
- Receiver role (hospital, research lab, insurance company)
- Purpose of sharing (treatment, research, insurance claim, clinical trial, commercial use)
- Patient Ethereum address
- Receiver Ethereum address
1.2. Identify any missing parameters for required tool calls.

2- Regulation Retrieval:
- Always call run_regulation_agent(...) first.
- If regulations are missing from the vector store → call web_search_for_regulations(...) and ask the user to approve the sources → re-run run_regulation_agent(...).
- If regulations prohibit sharing → stop the process.

3- Consent Validation:
- If regulations require consent → call run_consent_agent(...).
- If consent is missing or invalid → ask the user whether to call request_patient_consent(...).
- If the user declines → stop the process.

4- Data Filtering:
- If regulations allow all data types and anonymization is not required → skip filtering.
- Else → call run_filtering_agent(...) with the allowed data types and anonymization requirement.
- After filtering/anonymization → ask the user to approve the final file. If rejected → stop the process.

5- Data Sharing:
- If all previous steps succeed → call share_data(receiver_address) to send the file.


Human-in-the-Loop Triggers:
- Ask the user for input or approval in these situations:
- Missing any required parameter for a tool call
- Approval of web search sources for regulations
- Decision to request consent when it’s missing or invalid
- Approval of the final filtered/anonymized file


Output for Evaluation
For each scenario, output:
1- Route → ordered list of steps taken
2- Calls → list of function calls with parameters (use "<ASK_USER>" for missing ones)
3- Questions → list of questions to ask the user before proceeding

Output Format
For each scenario, return a JSON object:
{
  "route": [],
  "calls": [],
  "questions": []
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
        response = model.generate_content(
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
    print(f"✅ Evaluation complete. Results saved to {output_file}")



def call_claude(prompt: str, temperature: float = 0.0):
    start = time.time()
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            temperature=temperature,
            max_tokens=2048,
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


if __name__ == "__main__":
    INPUT_XLSX = "orchestratorDataset.xlsx"
    evaluate_gpt(INPUT_XLSX, "orchestrator_results_gpt.csv")
    evaluate_gemini(INPUT_XLSX, "orchestrator_results_gemini.csv")
    evaluate_claude(INPUT_XLSX, "orchestrator_results_claude.csv")
