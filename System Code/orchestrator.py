import streamlit as st
import asyncio
import base64
from openai import OpenAI
import os
import re
import json
import time
import requests
from web3 import Web3
from web3 import AsyncWeb3
from web3.providers.async_rpc import AsyncHTTPProvider
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
import subprocess


# Set up your API key
os.environ["OPENAI_API_KEY"] = ""
ORCHESTRATOR_ASSISTANT_ID = ""
VSID = ""
infuraUrl = ""
ethSenderKey = "";
ethSenderAddr = "";
AESKey = ""
pinata_secret_api_key = ""
pinata_api_key = ""

# Web3 setup
web3 = AsyncWeb3(AsyncHTTPProvider(infuraUrl))
assert web3.is_connected()

# Smart contract ABIs & addresses
consentSCAddr = "0x39daf39dc5999B19fc737AfF18B1513B477f4BFf";
dataSCAddr = "0xb9cf17726836E7c067124F947255329c31D23429";
consentSCAbi = []
dataSCAbi = []

if "consentSC" not in st.session_state:
    st.session_state.consentSC = web3.eth.contract(address=Web3.to_checksum_address(consentSCAddr), abi=consentSCAbi)
if "dataSC" not in st.session_state:
    st.session_state.dataSC = web3.eth.contract(address=Web3.to_checksum_address(dataSCAddr), abi=dataSCAbi)
consentSC = st.session_state.consentSC
dataSC = st.session_state.dataSC

client = OpenAI()

# Create threads for all agents
if "regThreadID" not in st.session_state:
    st.session_state.regThreadID = client.beta.threads.create().id
if "consentThreadID" not in st.session_state:
    st.session_state.consentThreadID = client.beta.threads.create().id
if "sharingThreadID" not in st.session_state:
    st.session_state.sharingThreadID = client.beta.threads.create().id
if "orchThreadID" not in st.session_state:
    st.session_state.orchThreadID = client.beta.threads.create().id

regThreadID = st.session_state.regThreadID
consentThreadID = st.session_state.consentThreadID
sharingThreadID = st.session_state.sharingThreadID
orchThreadID = st.session_state.orchThreadID

if "uploaded_file_name" in st.session_state:
    file_path = st.session_state.uploaded_file_name

output_path = "filtered_file.txt"

def submitToolOutputs(output, threadId, runId, callID):
    run = client.beta.threads.runs.submit_tool_outputs(
        thread_id=threadId,
        run_id=runId,
        tool_outputs=[
            {
                "tool_call_id": callID,
                "output": output
            }
        ]
    )
    return run


################################################## Orchestration Agent #######################################
async def run_orchestration_agent(user_input: str):
    print("🧠 Starting orchestration agent...")
    
    start = time.time()

    # Step 1: Add user input as a message
    client.beta.threads.messages.create(
        thread_id=orchThreadID,
        role="user",
        content=user_input
    )

    # Step 2: Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=orchThreadID,
        assistant_id=ORCHESTRATOR_ASSISTANT_ID
    )

    # Step 3: Poll for completion and get final message
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=orchThreadID,
            run_id=run.id
        )
        if run_status.status == "completed":
            # Retrieve assistant reply
            messages = client.beta.threads.messages.list(thread_id=orchThreadID)
            orchestratorResponse = messages.data[0].content[0].text.value  # Plain text response
            print("\n📘 Final Orchestrator Agent Response:\n")
            end = time.time()
            print("Orchestrator Time = ", (end-start))
            print(orchestratorResponse)
            return (orchestratorResponse)
        elif run_status.status in ["failed", "cancelled", "expired"]:
            raise Exception(f"Assistant run failed with status: {run_status.status}")
        elif (run_status.status == "requires_action" and run_status.required_action.type == "submit_tool_outputs"):
            if (run_status.required_action.submit_tool_outputs.tool_calls[0].function.name == "run_regulation_agent_tool"):
                callId = run_status.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run_status.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                regulations_query = f"I want the regulation requirements for sharing patient data from {arg['sender_country']} to a {arg['receiver_role']} in {arg['receiver_country']} for {arg['purpose']} purposes"
                print("Query for regulations agent: " + regulations_query)
                with st.status("📘 Calling Regulatory Compliance Agent to determine regulation requirements...", state="running", expanded=True) as status:
                    st.markdown(
                        '<span style="font-size:14px;">🔍 Retrieving regulations of sender and receiver countries...</span>',
                        unsafe_allow_html=True
                    )
                    st.session_state.chat_history.append({
                        "role": "status",
                        "agent": "Regulation Agent",
                        "label": "✓ 📘 Regulatory Compliance Agent analysis completed!",
                        "details": (
                            "🔍 Retrieving regulations of sender and receiver countries..."
                        )
                    })
                    regStart = time.time()
                    from regulatoryComplianceAgent import run_regulation_agent
                    output = await run_regulation_agent(regulations_query, regThreadID)
                    regEnd = time.time()
                    print("Regulation Agent Response Time = ", (regEnd-regStart))
                    submitToolOutputs(output, run.thread_id, run.id, callId)
                    st.markdown(
                        '<span style="font-size:14px;">✅ Regulatory Compliance Agent response received</span>',
                        unsafe_allow_html=True
                    )
                    status.update(
                        label="📘 Regulatory Compliance Agent analysis completed!", state="complete", expanded=False
                    )
                    for chat in st.session_state.chat_history:
                        if chat["role"] == "status" and chat["agent"] == "Regulation Agent":
                            chat["details"] += "\n ✅ Regulatory Compliance Agent response received"
                            break
                clean_output = re.sub(r'【\d+:\d+†.*?】', '', output)
                st.session_state.chat_history.append({
                    "role": "agent response",
                    "agent": "Regulation Agent Response",
                    "label": "📜 Regulatory Compliance Agent Response",
                    "details": clean_output
                })
            elif (run_status.required_action.submit_tool_outputs.tool_calls[0].function.name == "run_consent_agent_tool"):
                callId = run_status.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run_status.required_action.submit_tool_outputs.tool_calls[0].function.arguments)                
                consent_query = (
                    f"We want to share patient data.\n"
                    f"The sender is in {arg['sender_country']}, and the receiver is a {arg['receiver_role']} "
                    f"located in {arg['receiver_country']} with Ethereum address {arg['receiver_address']}.\n"
                    f"The purpose of sharing is: {arg['purposes']}.\n"
                    f"The patient's Ethereum address is {arg['patient_address']}.\n"
                    f"According to the regulation, the consent requirement is: {arg['consent_requirements']}.\n\n"
                    "Please check if valid consent exists and whether it satisfies this requirement and validate the receiver. If valid consent(s) exist, please return the full details of all the consent(s) that apply to this case."
                )
                print("Query for consent agent: "+ consent_query)
                with st.status("🔐 Calling Consent Verification Agent to validate required consents...", state="running", expanded=True) as status:
                    consentStart = time.time()
                    from consentVerificationAgent import run_consent_agent
                    output = await run_consent_agent(consent_query, consentThreadID)
                    consentEnd = time.time()
                    print("Consent Agent Response Time = ", (consentEnd-consentStart))
                    submitToolOutputs(output, run.thread_id, run.id, callId)
                    st.markdown(
                        '<span style="font-size:14px;">✅ Consent Verification Agent response received</span>',
                        unsafe_allow_html=True
                    )
                    status.update(
                        label="🔐 Consent Verification Agent analysis completed!", state="complete", expanded=False
                    )
                    for chat in st.session_state.chat_history:
                        if chat["role"] == "status" and chat["agent"] == "Consent Agent":
                            chat["details"] += "\n ✅ Consent Verification Agent response received"
                            break
                st.session_state.chat_history.append({
                    "role": "agent response",
                    "agent": "Consent Agent Response",
                    "label": "📜 Consent Verification Agent Response",
                    "details": output
                })
            elif (run_status.required_action.submit_tool_outputs.tool_calls[0].function.name == "run_data_filtering_tool"):
                callId = run_status.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run_status.required_action.submit_tool_outputs.tool_calls[0].function.arguments)                
                redaction_query = (
                    f"Please process the attached patient data file.\n\n"
                    f"The following data types are allowed to be shared: {arg['allowed_data_types']}.\n"
                )
                if arg["anonymization_required"]:
                    redaction_query += "Also, make sure the included data is properly anonymized before sharing, as anonymization is required in this case."
                else:
                    redaction_query += "Date anonymization is not required."
                print("Query for redaction agent: "+ redaction_query)
                with st.status("📝 Calling Data Filtering Agent to process the patient file...", state="running", expanded=True) as status:
                    filteringStart = time.time()
                    from dataFilteringAgent import run_data_filtering_agent
                    output = await run_data_filtering_agent(redaction_query, file_path, output_path, sharingThreadID)
                    filteringEnd = time.time()
                    print("Filtering Agent Response Time = ", (filteringEnd-filteringStart))
                    submitToolOutputs(output, run.thread_id, run.id, callId)
                    st.markdown(
                        '<span style="font-size:14px;">✅ Filtering and anonymization completed!</span>',
                        unsafe_allow_html=True
                    )
                    status.update(
                        label="📝 Data Filtering Agent analysis completed!", state="complete", expanded=False
                    )
                    for chat in st.session_state.chat_history:
                        if chat["role"] == "status" and chat["agent"] == "Data Filtering Agent":
                            chat["details"] += "\n ✅ Filtering and anonymization completed!"
                            break
            elif (run_status.required_action.submit_tool_outputs.tool_calls[0].function.name == "run_regulation_agent_tool_for_explanation"):
                callId = run_status.required_action.submit_tool_outputs.tool_calls[0].id
                with st.spinner("📘 Calling the Regulatory Compliance Agent to clarify data sharing rules..."):
                    regStart2 = time.time()
                    from regulatoryComplianceAgent import run_regulation_agent2
                    output = await run_regulation_agent2(user_input, regThreadID)
                    regEnd2 = time.time()
                    print("Regulation Agent Response Time for Questions = ", (regEnd2-regStart2))
                    submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run_status.required_action.submit_tool_outputs.tool_calls[0].function.name == "run_consent_agent_tool_for_explanation"):
                callId = run_status.required_action.submit_tool_outputs.tool_calls[0].id
                with st.spinner("🔐 Routing your question to the Consent Verification Agent for clarification..."):
                    consentStart2 = time.time()
                    from consentVerificationAgent import run_consent_agent2
                    output = await run_consent_agent2(user_input, consentThreadID)
                    consentEnd2 = time.time()
                    print("Consent Agent Response Time for Questions = ", (consentEnd2-consentStart2))
                    submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run_status.required_action.submit_tool_outputs.tool_calls[0].function.name == "run_data_filtering_tool_for_explanation"):
                callId = run_status.required_action.submit_tool_outputs.tool_calls[0].id
                with st.spinner("📝 Routing your question to the Data Filtering Agent for clarification..."):
                    filteringStart2 = time.time()
                    from dataFilteringAgent import run_data_filtering_agent3
                    output = await run_data_filtering_agent3(user_input, file_path, sharingThreadID)
                    filteringEnd2 = time.time()
                    print("Filtering Agent Response Time for Questions = ", (filteringEnd2-filteringStart2))
                    submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run_status.required_action.submit_tool_outputs.tool_calls[0].function.name == "requestGovernmentConsent"):
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                with st.spinner("🌐 Requesting government consent..."):
                    output = await requestGovernmentConsent(arg["receiver"], arg["country"], arg["dataTypes"], arg["purposes"])
                    submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run_status.required_action.submit_tool_outputs.tool_calls[0].function.name == "requestPatientConsent"):
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                with st.spinner("🌐 Requesting patient consent..."):
                    output = await requestPatientConsent(arg["patient"], arg["receiver"], arg["dataTypes"], arg["purposes"])
                    submitToolOutputs(output, run.thread_id, run.id, callId) 
            elif (run_status.required_action.submit_tool_outputs.tool_calls[0].function.name == "run_data_filtering_tool_for_extra_modifications"):
                callId = run_status.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run_status.required_action.submit_tool_outputs.tool_calls[0].function.arguments)                
                redaction_query = (
                    f"The user asked for the extra modifications as follows: {arg['user_request']}. Please re-filter the file again."
                )
                print("Query for redaction agent: "+ redaction_query)
                with st.spinner("📝 Calling the Data Filtering Agent for further data modifications..."):
                    from dataFilteringAgent import run_data_filtering_agent2
                    output = await run_data_filtering_agent2(redaction_query, output_path, sharingThreadID)
                    submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run_status.required_action.submit_tool_outputs.tool_calls[0].function.name == "data_sharing_tool"):
                callId = run_status.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run_status.required_action.submit_tool_outputs.tool_calls[0].function.arguments)                
                with st.status("📨 Sharing patient data...", state="running", expanded=True) as status:
                    sharingStart = time.time()
                    output = await shareData(arg["receiver_address"], output_path)
                    sharingEnd = time.time()
                    print("Full sharing time = ", (sharingEnd-sharingStart))
                    submitToolOutputs(output, run.thread_id, run.id, callId)
                    status.update(
                        label="📨 Data shared successfully via blockchain!", state="complete", expanded=False
                    )
            elif (run_status.required_action.submit_tool_outputs.tool_calls[0].function.name == "upload_web_sources_to_database"):
                callId = run_status.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run_status.required_action.submit_tool_outputs.tool_calls[0].function.arguments)                
                with st.spinner("🗃️ Adding retrieved regulations to the database..."):
                    output = save_webpage_as_pdf(arg["urls"])
                    submitToolOutputs(output, run.thread_id, run.id, callId)
                if "Failed" not in output:
                    text = "✅ Regulation files successfully uploaded to the vector store (ID: vs_685937bd583c819198aedb09b658b57f)"
                    with st.expander("🗃️ Retrieved regulation files added to the database!", expanded=False):
                        st.markdown(f'<div style="font-size:14px;">{text}</div>', unsafe_allow_html=True)
                    st.session_state.chat_history.append({
                        "role": "agent response",
                        "agent": "Regulation Agent Response",
                        "label": "✓ 🗃️ Retrieved regulation files added to the database!",
                        "details": text
                    })
            elif (run_status.required_action.submit_tool_outputs.tool_calls[0].function.name == "request_more_sources"):
                callId = run_status.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run_status.required_action.submit_tool_outputs.tool_calls[0].function.arguments)                
                with st.spinner("🔍 Searching the web for additional regulatory sources..."):
                    output = await run_web_search_tool2(arg["query"], arg["previous_urls"], arg["user_response"])
                    submitToolOutputs(output, run.thread_id, run.id, callId)    


async def requestGovernmentConsent(receiver: str, country: str, dataTypes: list, purposes: list):
    government = await dataSC.functions.getGovernmentAddress(country).call()
    tx = await consentSC.functions.requestGovernmentConsent(
        Web3.to_checksum_address(government),
        Web3.to_checksum_address(receiver),
        dataTypes,
        purposes
    ).build_transaction({
        'from': Web3.to_checksum_address(ethSenderAddr),
        'nonce': await web3.eth.get_transaction_count(Web3.to_checksum_address(web3.eth.account.from_key(ethSenderKey).address)),
        'gas': 3000000,
        'gasPrice': await web3.eth.gas_price
    })
    signed = web3.eth.account.sign_transaction(tx, ethSenderKey)
    tx_hash = await web3.eth.send_raw_transaction(signed.rawTransaction)
    print("📤 Consent request sent via blockchain.")
    return ("📤 Consent request sent via blockchain. Transaction hash: " + tx_hash.hex())

async def requestPatientConsent(patient: str, receiver: str, dataTypes: list, purposes: list):
    tx = await consentSC.functions.requestPatientConsent(
        Web3.to_checksum_address(patient),
        Web3.to_checksum_address(receiver),
        dataTypes,
        purposes
    ).build_transaction({
        'from': Web3.to_checksum_address(ethSenderAddr),
        'nonce': await web3.eth.get_transaction_count(Web3.to_checksum_address(web3.eth.account.from_key(ethSenderKey).address)),
        'gas': 3000000,
        'gasPrice': await web3.eth.gas_price
    })
    signed = web3.eth.account.sign_transaction(tx, ethSenderKey)
    tx_hash = await web3.eth.send_raw_transaction(signed.rawTransaction)
    print("📤 Consent request sent via blockchain.")
    return ("📤 Consent request sent via blockchain. Transaction hash: " + tx_hash.hex())

async def run_web_search_tool2(query: str, original_urls: str, user_response: str):

    url_instruction2 = f"""
You are a compliance assistant helping search for global healthcare data-sharing regulations.

Please identify the official regulation documents for the sender and receiver countries in the following scenario:

\"\"\"{query}\"\"\"

You are originally provided these URLs:

\"\"\"{original_urls}\"\"\"

And the user said this:

\"\"\"{user_response}\"\"\"

So the user wants more trusted URLs. Provide new more webpage URLs that are very trusted and from official and goverment sources only!!! 
If no enough official webpages found you can use unofficial sources.
Return only a numbered list of URLs (not more than 10)!
Do NOT provide summaries or any interpretation. 
You have to return URLs/links (starts with http....) of sources include the needed information!

✅ Format your response as follows (EXACTLY):
1- https://...

2- https://...

3- https://...
"""

    response2 = client.responses.create(
        model="gpt-4o",
        tools=[{"type": "web_search_preview"}],
        tool_choice="required",
        input="Search for official healthcare data-sharing laws of both receiver and sender countries and return a list of URLs that include the needed information. Do not include any explanation or interpretation.",
        instructions=url_instruction2,
        temperature=0,
    ) 
    print("\nURLs:\n")
    print(response2.output_text)

    return "New URLs: " + response2.output_text

def save_webpage_as_pdf(urls: str):
    try:
        result = subprocess.run(
            ["python", "save_webpages_worker.py", urls],
            check=True,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        return "✅ Files saved to database successfully."
    except subprocess.CalledProcessError as e:
        print(e.stderr)
        return "❌ Failed to save PDFs."

def upload_to_vector_store(filepath: str, vector_store_id: str):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    print(f"📁 Uploading file: {filepath}")
    upload_response = client.files.create(
        file=open(filepath, "rb"),
        purpose="user_data"
    )

    file_id = upload_response.id
    print(f"✅ File uploaded. File ID: {file_id}")

    print(f"📦 Attaching file to vector store: {vector_store_id}")
    vs_response = client.vector_stores.files.create(
        vector_store_id=vector_store_id,
        file_id=file_id
    )

    print("📌 File successfully added to vector store.")



################################################## Sharing Data ##############################################
async def shareData(receiver: str, output_path: str):
    st.markdown(
        '<span style="font-size:14px;">🔑 Getting receiver public key from blockchain...</span>',
        unsafe_allow_html=True
    )
    st.session_state.chat_history.append({
        "role": "status",
        "agent": "Data Filtering Agent",
        "label": "✓ 📨 Data shared successfully via blockchain!",
        "details": (
            "🔑 Getting receiver public key from blockchain...\n🔐 Encrypting patient file with receiver key...\n🌐 Uploading encrypted file to IPFS...\n⛓️ Writing transaction to blockchain..."
        )
    })
    receiverKey = await getReceiverKey(receiver)
    st.markdown(
        '<span style="font-size:14px;">🔐 Encrypting patient file with receiver key...</span>',
        unsafe_allow_html=True
    )
    encryptedData = encrypt_file_symmetric(output_path, base64.b64decode(AESKey))
    st.markdown(
        '<span style="font-size:14px;">🌐 Uploading encrypted file to IPFS...</span>',
        unsafe_allow_html=True
    )
    CID = upload_text_to_ipfs(encryptedData, pinata_api_key, pinata_secret_api_key)
    encryptedCID = encrypt_cid_with_rsa(receiverKey, CID)
    st.markdown(
        '<span style="font-size:14px;">⛓️ Writing transaction to blockchain...</span>',
        unsafe_allow_html=True
    )
    hash = await shareDataSC(receiver, ("0x" + encryptedCID.hex()))
    return hash

async def getReceiverKey(address: str):
    receiverKey = await dataSC.functions.getUserPublicKey(address).call() 
    return receiverKey

async def shareDataSC(receiver: str, data):
    tx = await dataSC.functions.shareData(
        Web3.to_checksum_address(receiver),
        data
    ).build_transaction({
        'from': Web3.to_checksum_address(ethSenderAddr),
        'nonce': await web3.eth.get_transaction_count(Web3.to_checksum_address(web3.eth.account.from_key(ethSenderKey).address)),
        'gas': 3000000,
        'gasPrice': await web3.eth.gas_price
    })
    signed = web3.eth.account.sign_transaction(tx, ethSenderKey)
    tx_hash = await web3.eth.send_raw_transaction(signed.rawTransaction)
    print("📤 Data is sent to receiver via blockchain. Transaction hash: " + tx_hash.hex())
    return tx_hash.hex()

def upload_file_to_ipfs(file_path: str, pinata_api_key: str, pinata_secret_api_key: str) -> str:
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": pinata_api_key,
        "pinata_secret_api_key": pinata_secret_api_key,
    }

    with open(file_path, 'rb') as file:
        files = {
            'file': (file_path, file)
        }
        response = requests.post(url, files=files, headers=headers)

    if response.status_code == 200:
        cid = response.json()["IpfsHash"]
        print(f"✅ File uploaded to IPFS via Pinata. CID: {cid}")
        return cid
    else:
        raise Exception(f"❌ Pinata upload failed: {response.status_code} - {response.text}")
    
def upload_text_to_ipfs(encrypted_data: str, pinata_api_key: str, pinata_secret_api_key: str, name: str = "encrypted-data") -> str:
    url = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
    headers = {
        "Content-Type": "application/json",
        "pinata_api_key": pinata_api_key,
        "pinata_secret_api_key": pinata_secret_api_key,
    }

    payload = {
        "pinataOptions": {"cidVersion": 1},
        "pinataMetadata": {"name": name},
        "pinataContent": {
            "encrypted_data": base64.b64encode(encrypted_data).decode('utf-8')
        }
    }

    response = requests.post(url, data=json.dumps(payload), headers=headers)

    if response.status_code == 200:
        cid = response.json()["IpfsHash"]
        print(f"✅ Encrypted data uploaded to IPFS. CID: {cid}")
        return cid
    else:
        raise Exception(f"❌ Failed to upload to IPFS: {response.status_code} - {response.text}")

def encrypt_file_symmetric(input_file_path: str, key: bytes) -> bytes:
    # Read plain text from file
    with open(input_file_path, 'rb') as f:
        plaintext = f.read()

    # Pad plaintext to block size
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plaintext) + padder.finalize()

    # Generate random IV (initialization vector)
    iv = os.urandom(16)

    # Create AES cipher in CBC mode
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data) + encryptor.finalize()

    # Return base64-encoded ciphertext + IV
    return base64.b64encode(iv + ciphertext)

def encrypt_cid_with_rsa(public_key_der: bytes, cid: str):
    # Load RSA public key from DER bytes
    public_key = serialization.load_der_public_key(public_key_der)

    # Encrypt CID
    encrypted = public_key.encrypt(
        cid.encode('utf-8'),
        asym_padding.PKCS1v15()
    )

    # Return base64-encoded ciphertext
    return base64.b64encode(encrypted)



#################################################### Chatbot UI ##############################################
# Load image as base64 for the title avatar
def get_base64_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

# CSS for chay UI
st.markdown("""
    <style>
    div[data-testid="stChatMessage"] {
        margin-bottom: -12px !important;
        margin-top: -12px !important;
        background: transparent !important;
    }

    div[data-testid="stChatMessage"] .stMarkdown {
        padding-bottom: -12px !important;
        padding-top: -12px !important;
        line-height: 1.3;
        font-size: 25px !important;
    }

    .stChatAvatar {
        width: 40px !important;
        height: 40px !important;
        margin-left: 0px;
        margin-right: 6px;
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
    }

    .title-box {
        border: 2px solid #ccc;
        border-radius: 12px;
        padding: 8px 10px;
        margin-bottom: 10px;
        font-size: 26px;
        font-weight: bold;
        background-color: #f9f9f9;
        text-align: center;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
    }
            
    div[data-testid="stExpander"] summary {
    	font-size: 24px !important;
	}

	/* Ensure children (p/span) inherit */
	div[data-testid="stExpander"] summary * {
    	font-size: 25px !important;
	}
    </style>
""", unsafe_allow_html=True)

# Title
st.set_page_config(page_title="Healthcare Assistant", layout="wide")
image_base64 = get_base64_image("bot.png")  # Replace with your real bot image path
st.markdown(f"""
    <div class="title-box">
        <img src="data:image/png;base64,{image_base64}" width="28" style="vertical-align: middle; margin-right: 4px; margin-top: -4px;">
        <strong>Healthcare Data Sharing Assistant</strong>
    </div>
""", unsafe_allow_html=True)

# Initialize State
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "file_uploaded" not in st.session_state:
    st.session_state.file_uploaded = False
if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None

# Display Chat Messages
for chat in st.session_state.chat_history:
    if chat["role"] == "user":
        with st.chat_message("user", avatar="white.png"):
            image_base64 = get_base64_image("user.png")
            st.markdown(
                f"""
                <div style="display: flex; justify-content: flex-end; margin-bottom: 8px;">
                    <div style="background-color: #d1e7dd; padding: 10px 14px; border-radius: 12px; font-size: 25px; max-width: 80%; text-align: left;">
                        {chat["message"]}
                    </div>
                    <img src="data:image/png;base64,{image_base64}" width="36" height="36" style="margin-left: 8px; margin-top: 4px;">
                </div>
                """,
                unsafe_allow_html=True
            )
    elif chat["role"] == "assistant":
        with st.chat_message("assistant", avatar="bot.png"):
            st.markdown(
                f"""
                <div style="display: flex; align-items: flex-start; margin-bottom: 8px;">
                    <div style="background-color: #e2e3e5; padding: 10px 14px; border-radius: 12px; font-size: 25px;">
                        {chat["message"]}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    elif chat["role"] == "status":
        with st.expander(chat["label"], expanded=False):
            formatted_details = chat["details"].replace("\n", "<br>")
            styled_details = f'<div style="font-size:22px;">{formatted_details}</div>'
            st.markdown(styled_details, unsafe_allow_html=True)

# File Upload (Show Once) 
if not st.session_state.file_uploaded:
    uploaded_file = st.file_uploader("", type=["pdf", "txt", "csv", "docx"])
    if uploaded_file:
        st.session_state.uploaded_file_name = uploaded_file.name
        file_path = st.session_state.uploaded_file_name
        st.session_state.file_uploaded = True
        st.session_state.file_pending_display = True

# Chat Input
user_input = st.chat_input("Describe your case or ask a question...")

# Send Message 
if user_input:
    # Combine message with file info if uploaded
    message = user_input
    if st.session_state.get("file_pending_display", False):
        message += f"\n\n \n\n🔗 Attached file: **{st.session_state.uploaded_file_name}**"
        st.session_state.file_pending_display = False

    # Add user message
    st.session_state.chat_history.append({"role": "user", "message": message})
    with st.chat_message("user", avatar="white.png"):
        image_base64 = get_base64_image("user.png")
        st.markdown(
            f"""
            <div style="display: flex; justify-content: flex-end; margin-bottom: 8px;">
                <div style="background-color: #d1e7dd; padding: 10px 14px; border-radius: 12px; font-size: 25px; max-width: 80%; text-align: left;">
                    {message}
                </div>
                <img src="data:image/png;base64,{image_base64}" width="36" height="36" style="margin-left: 8px; margin-top: 4px;">
            </div>
            """,
            unsafe_allow_html=True
        )

    # Simulate assistant
    with st.spinner("🧠 Processing..."):
        response = asyncio.run(run_orchestration_agent(user_input))

    # Add assistant message
    st.session_state.chat_history.append({"role": "assistant", "message": response})
    with st.chat_message("assistant", avatar="bot.png"):
        st.markdown(
            f"""
            <div style="display: flex; align-items: flex-start; margin-bottom: 8px;">
                <div style="background-color: #e2e3e5; padding: 10px 14px; border-radius: 12px; font-size: 25px;">
                    {response}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
