import os
import time
import pandas as pd
from tqdm import tqdm
from together import Together
from langchain.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from openai import OpenAI
import google.generativeai as genai
import anthropic

# === CONFIG ===
os.environ["OPENAI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["TOGETHER_API_KEY"] = ""

client = OpenAI()
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
gemini_model = genai.GenerativeModel("gemini-2.5-pro")
claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
client = Together()

REGULATION_FOLDER = "./regulations"
INDEX_PATH = "./faiss_index"

# === SYSTEM PROMPT ===
SYSTEM_INSTRUCTIONS = {
  "role": "system",
  "content": """
  You are a Healthcare Data Regulation Assistant. Your job is to interpret and evaluate whether healthcare data can be legally shared between two countries based on their regulations.

You will receive:
- A sender country
- A receiver country

You will also have access to **attached regulation documents** for each country, which contain the official rules regarding cross-border healthcare data sharing.

Your task is to answer the following **four questions**, using the your internal knowledge and the information in the attached documents and following this evaluation logic:

1. **Is anonymization required?**
   - Answer "Yes" if **either** the sender or receiver country requires anonymization for cross-border data sharing (even if only for certain data types or purposes).
   - Otherwise, answer "No".

2. **What type of patient consent is required?**
  - Return one of the following options based on the most restrictive requirement:"
    - `None` → if both countries allow sharing without consent"
    - `Broad` → if at least one country requires broad/general consent"
    - `Specific` → if at least one country requires consent tailored to the receiver, role, or purpose"
    - `Explicit` → if either country explicitly requires written or formal consent"
  - Always return the most specific or highest-level consent required."   

3. **Is government or authority approval required?**
   - Answer "Yes" if **either** country requires approval from a **government, health authority, data protection authority, or regulator** before sharing data across borders.
   - Otherwise, answer "No".

4. **What types of data and purposes are allowed to be shared?**
   - List the data types and purposes that are permitted by both the sender and receiver.
   - If a data type is allowed in one country but **restricted or prohibited** in the other, do **not** include it.
   - Use phrases like `"Clinical Notes, Genomic data, Treatment, Research"`, etc.
   - Ensure that consent and any safeguards (e.g., encryption or anonymization) are assumed to be in place if required.

---

Output your final answer in the following JSON format:

{
  \"anonymization_required\": Yes or No,
  \"patient_consent_required\": the type of required patient consent,
  \"government_approval_required\": Yes or No,
  \"allowed_data_and_purposes\": list of allowed data types and purposes
}

---

Use your internal knowledge and the content found in the attached country regulation documents* (HIPAA, GDPR, UAE Health Law, PDPA, etc.).

Think carefully and reason step-by-step before generating your response. You should answer based on both countries regulations!!
"""
}
# === Build Vector Store ===
def build_vectorstore():
    documents = []
    for fname in os.listdir(REGULATION_FOLDER):
        if fname.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(REGULATION_FOLDER, fname))
            docs = loader.load()
            documents.extend(docs)

    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = []
    for doc in documents:
        chunks.extend(splitter.split_documents([doc]))

    print(f"✅ Total chunks: {len(chunks)}")

    embeddings = OpenAIEmbeddings()
    texts = [doc.page_content for doc in chunks]
    metadatas = [doc.metadata for doc in chunks]

    batch_size = 50
    text_embedding_pairs = []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_embeddings = embeddings.embed_documents(batch_texts)
        text_embedding_pairs.extend(zip(batch_texts, batch_embeddings))

    faiss_index = FAISS.from_embeddings(
        text_embeddings=text_embedding_pairs,
        metadatas=metadatas,
        embedding=embeddings
    )
    faiss_index.save_local(INDEX_PATH)
    print("✅ Vector store built and saved.")

# === Load Vector Store ===
def load_vectorstore():
    embeddings = OpenAIEmbeddings()
    return FAISS.load_local(INDEX_PATH, embeddings, allow_dangerous_deserialization=True)

# === RAG Inference ===
def retrieve_context(vectorstore, sender, receiver, k=5):
    query = f"Healthcare data sharing regulations for {sender} and {receiver}"
    docs = vectorstore.similarity_search(query, k=k)
    return "\n\n".join(doc.page_content for doc in docs)

def call_together_model(vectorstore, sender, receiver, model_name):
    context = retrieve_context(vectorstore, sender, receiver)
    print(f"Context retrieved: {context}")
    prompt = f"Context:\n{context}\n\nSender Country: {sender}\nReceiver Country: {receiver}\n\nAnswer in JSON:\n"

    start = time.time()
    try:
        response = client.responses.create(
            model=model_name,
            instructions=SYSTEM_INSTRUCTIONS["content"],
            input=prompt,
            temperature=0.0
        )
        duration = round(time.time() - start, 2)
        return response.output_text.strip(), duration
    except Exception as e:
        return f"Error: {e}", -1

def evaluate_gpt(input_xlsx, output_csv, sheet_name="Sheet1"):
    vectorstore = load_vectorstore()
    df = pd.read_excel(input_xlsx, sheet_name=sheet_name)
    if not all(col in df.columns for col in ["Sender", "Receiver"]):
        raise ValueError("Input file must contain columns: Sender, Receiver")

    results = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating with Together.ai"):
        sender = row["Sender"]
        receiver = row["Receiver"]
        response, duration = call_together_model(vectorstore, sender, receiver, "gpt-4.1")
        results.append({
            "Sender": sender,
            "Receiver": receiver,
            "Response Time (s)": duration,
            "Raw Response": response
        })

    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Results saved to {output_csv}")



def call_gemini(vectorstore, sender, receiver):
    context = retrieve_context(vectorstore, sender, receiver)
    prompt = f"{SYSTEM_INSTRUCTIONS["content"]}\n\n{context}\n\nSender Country: {sender}\nReceiver Country: {receiver}"

    start = time.time()
    try:
        response = gemini_model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.0
            }
        )
        return response.text.strip(), round(time.time() - start, 2)
    except Exception as e:
        return f"Error: {e}", -1

def evaluate_gemini(input_xlsx: str, output_csv: str, sheet_name="Sheet1"):
    vectorstore = load_vectorstore()
    df = pd.read_excel(input_xlsx, sheet_name=sheet_name)
    if not all(col in df.columns for col in ["Sender", "Receiver"]):
        raise ValueError("Excel must contain 'Sender' and 'Receiver' columns.")

    results = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating Cases"):
        sender = row["Sender"]
        receiver = row["Receiver"]
        response, duration = call_gemini(vectorstore, sender, receiver)

        results.append({
            "Sender": sender,
            "Receiver": receiver,
            "Response Time (s)": duration,
            "Raw Response": response
        })

    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Results saved to {output_csv}")



def call_claude(vectorstore, sender, receiver):
    context = retrieve_context(vectorstore, sender, receiver)
    full_prompt = f"""
Context:
{context}

Sender Country: {sender}
Receiver Country: {receiver}

Answer in JSON:
"""

    start = time.time()
    try:
        response = claude.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            temperature=0.0,
            system=SYSTEM_INSTRUCTIONS["content"],
            messages=[
                {"role": "user", "content": full_prompt}
            ]
        )
        return response.content[0].text.strip(), round(time.time() - start, 2)
    except Exception as e:
        return f"Error: {e}", -1

def evaluate_claude(input_xlsx: str, output_csv: str, sheet_name="Sheet1"):
    vectorstore = load_vectorstore()
    df = pd.read_excel(input_xlsx, sheet_name=sheet_name)
    if not all(col in df.columns for col in ["Sender", "Receiver"]):
        raise ValueError("Excel must contain 'Sender' and 'Receiver' columns.")

    results = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating with Claude"):
        sender = row["Sender"]
        receiver = row["Receiver"]
        response, duration = call_claude(vectorstore, sender, receiver)
        results.append({
            "Sender": sender,
            "Receiver": receiver,
            "Response Time (s)": duration,
            "Raw Response": response
        })

    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Saved results to {output_csv}")



def evaluate_deepseek(input_xlsx, output_csv, sheet_name="Sheet1"):
    vectorstore = load_vectorstore()
    df = pd.read_excel(input_xlsx, sheet_name=sheet_name)
    if not all(col in df.columns for col in ["Sender", "Receiver"]):
        raise ValueError("Input file must contain columns: Sender, Receiver")

    results = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating with Together.ai"):
        sender = row["Sender"]
        receiver = row["Receiver"]
        response, duration = call_together_model(vectorstore, sender, receiver, "deepseek-ai/DeepSeek-V3")
        results.append({
            "Sender": sender,
            "Receiver": receiver,
            "Response Time (s)": duration,
            "Raw Response": response
        })

    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Results saved to {output_csv}")



def evaluate_mistral(input_xlsx, output_csv, sheet_name="Sheet1"):
    vectorstore = load_vectorstore()
    df = pd.read_excel(input_xlsx, sheet_name=sheet_name)
    if not all(col in df.columns for col in ["Sender", "Receiver"]):
        raise ValueError("Input file must contain columns: Sender, Receiver")

    results = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating with Together.ai"):
        sender = row["Sender"]
        receiver = row["Receiver"]
        response, duration = call_together_model(vectorstore, sender, receiver, "mistral-medium-2505")
        results.append({
            "Sender": sender,
            "Receiver": receiver,
            "Response Time (s)": duration,
            "Raw Response": response
        })

    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Results saved to {output_csv}")



def evaluate_qwen(input_xlsx, output_csv, sheet_name="Sheet1"):
    vectorstore = load_vectorstore()
    df = pd.read_excel(input_xlsx, sheet_name=sheet_name)
    if not all(col in df.columns for col in ["Sender", "Receiver"]):
        raise ValueError("Input file must contain columns: Sender, Receiver")

    results = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Evaluating with Together.ai"):
        sender = row["Sender"]
        receiver = row["Receiver"]
        response, duration = call_together_model(vectorstore, sender, receiver, "Qwen/Qwen3-235B-A22B-fp8-tput")
        results.append({
            "Sender": sender,
            "Receiver": receiver,
            "Response Time (s)": duration,
            "Raw Response": response
        })

    pd.DataFrame(results).to_csv(output_csv, index=False)
    print(f"✅ Results saved to {output_csv}")



# === Main ===
if __name__ == "__main__":
    # Step 1: Build the vector store ONCE
    if not os.path.exists(os.path.join(INDEX_PATH, "index.faiss")):
        build_vectorstore()

    # Step 2: Evaluate all sender–receiver pairs
    INPUT_XLSX = "RegulationDataset.xlsx"
    evaluate_gpt(INPUT_XLSX, "regulation_results_gpt.csv")
    evaluate_gemini(INPUT_XLSX, "regulation_results_gemini.csv")
    evaluate_claude(INPUT_XLSX, "regulation_results_claude.csv")
    evaluate_deepseek(INPUT_XLSX, "regulation_results_deepseek.csv")
    evaluate_mistral(INPUT_XLSX, "regulation_results_mistral.csv")
    evaluate_qwen(INPUT_XLSX, "regulation_results_qwen.csv")
