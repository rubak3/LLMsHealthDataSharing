import streamlit as st
from openai import OpenAI
import os
import json
from web3 import Web3
from web3 import AsyncWeb3
from web3.providers.async_rpc import AsyncHTTPProvider


# Set up your API key
os.environ["OPENAI_API_KEY"] = ""
CONSENT_ASSISTANT_ID = ""
infuraUrl = ""

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


DATA_TYPE_MAP = {
    1: "Clinical Notes & Diagnosis",
    2: "Lab & Test Results",
    3: "Genomic Data",
    4: "Mental Health Data",
    5: "PHRs (e.g. Device Records)",
    6: "Medical History",
    7: "All Data Types"
}

PURPOSE_MAP = {
    1: "Treatment",
    2: "Research",
    3: "Insurance Claim",
    4: "Clinical Trial",
    5: "Commercial Use",
    6: "All Pusposes"
}

async def run_consent_agent(user_input: str, threadId: str) -> str:

    # Step 1: Add user message
    client.beta.threads.messages.create(
        thread_id=threadId,
        role="user",
        content=user_input
    )

    # Step 2: Start a run with the assistant
    run = client.beta.threads.runs.create(
        thread_id=threadId,
        assistant_id=CONSENT_ASSISTANT_ID
    )

    # Step 3: Get the assistant response
    while True:
        messages = client.beta.threads.messages.list(thread_id=threadId)
        run = client.beta.threads.runs.retrieve(
            thread_id=threadId,
            run_id=run.id
        )
        if (run.status == "requires_action" and run.required_action.type == "submit_tool_outputs"):
            if (run.required_action.submit_tool_outputs.tool_calls[0].function.name == "getSpecificConsent"):
                st.markdown(
                    '<span style="font-size:14px;">🔍 Searching for valid patient consent...</span>',
                    unsafe_allow_html=True
                )
                st.session_state.chat_history.append({
                    "role": "status",
                    "agent": "Consent Agent",
                    "label": "✓ 🔐 Consent Verification Agent analysis completed!",
                    "details": (
                        "🔍 Searching for valid patient consent..."
                    )
                })
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                output = await getSpecificConsent(arg["patient"], arg["receiver"])
                submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run.required_action.submit_tool_outputs.tool_calls[0].function.name == "getGovernmentConsent"):
                st.markdown(
                    '<span style="font-size:14px;">🔍 Searching for valid government consent...</span>',
                    unsafe_allow_html=True
                )
                for chat in st.session_state.chat_history:
                        if chat["role"] == "status" and chat["agent"] == "Consent Agent":
                            chat["details"] += "\n 🔍 Searching for valid government consent..."
                            break
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                output = await getGovernmentConsent(arg["country"], arg["receiver"])
                submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run.required_action.submit_tool_outputs.tool_calls[0].function.name == "getUniversalConsents"):
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                output = await getUniversalConsents(arg["patient"])
                submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run.required_action.submit_tool_outputs.tool_calls[0].function.name == "getHospitalConsents"):
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                output = await getHospitalConsents(arg["patient"])
                submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run.required_action.submit_tool_outputs.tool_calls[0].function.name == "getResearchLabConsents"):
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                output = await getResearchLabConsents(arg["patient"])
                submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run.required_action.submit_tool_outputs.tool_calls[0].function.name == "getInsuranceCompanyConsents"):
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                output = await getInsuranceConsents(arg["patient"])
                submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run.required_action.submit_tool_outputs.tool_calls[0].function.name == "validateReceiver"):
                st.markdown(
                    '<span style="font-size:14px;">⚙️ Validating the receiver...</span>',
                    unsafe_allow_html=True
                )
                for chat in st.session_state.chat_history:
                        if chat["role"] == "status" and chat["agent"] == "Consent Agent":
                            chat["details"] += "\n ⚙️ Validating the receiver..."
                            break
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                output = await validateReceiver(arg["address"], arg["role"])
                submitToolOutputs(output, run.thread_id, run.id, callId)
        elif (messages.data and messages.data[0].role == "assistant" and len(messages.data[0].content) > 0):
            st.markdown(
                    '<span style="font-size:14px;">🧠 Consent Verification Agent is reasoning...</span>',
                    unsafe_allow_html=True
                )
            for chat in st.session_state.chat_history:
                        if chat["role"] == "status" and chat["agent"] == "Consent Agent":
                            chat["details"] += "\n 🧠 Consent Verification Agent is reasoning..."
                            break
            consentAgentResponse = messages.data[0].content[0].text.value
            print("Consent Validation Agent Response: ")
            print(consentAgentResponse)
            break 
    
    return consentAgentResponse

async def run_consent_agent2(user_input: str, threadId: str) -> str:

    # Step 1: Add user message
    client.beta.threads.messages.create(
        thread_id=threadId,
        role="user",
        content=user_input
    )

    # Step 2: Start a run with the assistant
    run = client.beta.threads.runs.create(
        thread_id=threadId,
        assistant_id=CONSENT_ASSISTANT_ID
    )

    # Step 3: Get the assistant response
    while True:
        messages = client.beta.threads.messages.list(thread_id=threadId)
        run = client.beta.threads.runs.retrieve(
            thread_id=threadId,
            run_id=run.id
        )
        if (run.status == "requires_action" and run.required_action.type == "submit_tool_outputs"):
            if (run.required_action.submit_tool_outputs.tool_calls[0].function.name == "getSpecificConsent"):
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                output = await getSpecificConsent(arg["patient"], arg["receiver"])
                submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run.required_action.submit_tool_outputs.tool_calls[0].function.name == "getGovernmentConsent"):
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                output = await getGovernmentConsent(arg["country"], arg["receiver"])
                submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run.required_action.submit_tool_outputs.tool_calls[0].function.name == "getUniversalConsents"):
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                output = await getUniversalConsents(arg["patient"])
                submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run.required_action.submit_tool_outputs.tool_calls[0].function.name == "getHospitalConsents"):
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                output = await getHospitalConsents(arg["patient"])
                submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run.required_action.submit_tool_outputs.tool_calls[0].function.name == "getResearchLabConsents"):
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                output = await getResearchLabConsents(arg["patient"])
                submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run.required_action.submit_tool_outputs.tool_calls[0].function.name == "getInsuranceCompanyConsents"):
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                output = await getInsuranceConsents(arg["patient"])
                submitToolOutputs(output, run.thread_id, run.id, callId)
            elif (run.required_action.submit_tool_outputs.tool_calls[0].function.name == "validateReceiver"):
                callId = run.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                output = await validateReceiver(arg["address"], arg["role"])
                submitToolOutputs(output, run.thread_id, run.id, callId)
        elif (messages.data and messages.data[0].role == "assistant" and len(messages.data[0].content) > 0):
            consentAgentResponse = messages.data[0].content[0].text.value
            print("Consent Agent Response: ")
            print(consentAgentResponse)
            break 
    
    return consentAgentResponse

# Calling SC functions
async def getSpecificConsent(patient: str, receiver: str):
    response = await consentSC.functions.getSpecificConsents(patient, receiver).call()
    if (not response or (
        len(response) == 1 and
        response[0][0] == '0x0000000000000000000000000000000000000000' and
        response[0][5] is False)):
        specificConsent = "No specific consent available for the specific receiver"
    else:
        # Convert to a JSON-style list of dicts
        specificConsent = [
            {
                "Receiver Address": r[0],
                "Data Types": [DATA_TYPE_MAP.get(d, f"Unknown({d})") for d in r[1]],
                "Purposes": [PURPOSE_MAP.get(p, f"Unknown({p})") for p in r[2]],
                "Anonymity": r[3],
                "Duration": r[4],
                "Active": r[5],
                "ConsentID": r[6]
            }
            for r in response
        ]
    return json.dumps(specificConsent)

async def getGovernmentConsent(country: str, receiver: str):
    government = await dataSC.functions.getGovernmentAddress(country).call()
    response = await consentSC.functions.getGovernmentConsents(government, receiver).call()
    if (not response or (
        len(response) == 1 and
        response[0][0] == '0x0000000000000000000000000000000000000000' and
        response[0][5] is False)):
        governmentConsents = "No government consent available for the specific receiver"
    else:
        # Convert to a JSON-style list of dicts
        governmentConsents = [
            {
                "Data Types": [DATA_TYPE_MAP.get(d, f"Unknown({d})") for d in r[0]],
                "Purposes": [PURPOSE_MAP.get(p, f"Unknown({p})") for p in r[1]],
                "Receiver Address": r[2],
                "Active": r[3],
                "ConsentID": r[4]
            }
            for r in response
        ]
    return json.dumps(governmentConsents)

async def getUniversalConsents(patient: str):
    response = await consentSC.functions.getUniversalConsents(patient).call()
    if not response:
        universalConsents = "No universal consents available for this patient"
    else:
        # Convert to a JSON-style list of dicts
        universalConsents = [
            {
                "Data Types": [DATA_TYPE_MAP.get(d, f"Unknown({d})") for d in r[0]],
                "Purposes": [PURPOSE_MAP.get(p, f"Unknown({p})") for p in r[1]],
                "Receiver Locations": r[2],
                "Anonymity": r[3],
                "Duration": r[4],
                "Active": r[5],
                "ConsentID": r[6]
            }
            for r in response
        ]
    return json.dumps(universalConsents)

async def getHospitalConsents(patient: str):
    response = await consentSC.functions.getHospitalConsents(patient).call()
    if not response:
        hospitalConsents = "No hospital consents available for this patient"
    else:
        # Convert to a JSON-style list of dicts
        hospitalConsents = [
            {
                "Data Types": [DATA_TYPE_MAP.get(d, f"Unknown({d})") for d in r[0]],
                "Purposes": [PURPOSE_MAP.get(p, f"Unknown({p})") for p in r[1]],
                "Receiver Locations": r[2],
                "Anonymity": r[3],
                "Duration": r[4],
                "Active": r[5],
                "ConsentID": r[6]
            }
            for r in response
        ]
    return json.dumps(hospitalConsents)

async def getResearchLabConsents(patient: str):
    response = await consentSC.functions.getLabConsents(patient).call()
    if not response:
        labConsents = "No research lab consents available for this patient"
    else:
        # Convert to a JSON-style list of dicts
        labConsents = [
            {
                "Data Types": [DATA_TYPE_MAP.get(d, f"Unknown({d})") for d in r[0]],
                "Purposes": [PURPOSE_MAP.get(p, f"Unknown({p})") for p in r[1]],
                "Receiver Locations": r[2],
                "Anonymity": r[3],
                "Duration": r[4],
                "Active": r[5],
                "ConsentID": r[6]
            }
            for r in response
        ]
    return json.dumps(labConsents)

async def getInsuranceConsents(patient: str):
    response = await consentSC.functions.getInsuranceConsents(patient).call()
    if not response:
        insuranceConsents = "No insurance company consents available for this patient"
    else:
        # Convert to a JSON-style list of dicts
        insuranceConsents = [
            {
                "Data Types": [DATA_TYPE_MAP.get(d, f"Unknown({d})") for d in r[0]],
                "Purposes": [PURPOSE_MAP.get(p, f"Unknown({p})") for p in r[1]],
                "Receiver Locations": r[2],
                "Anonymity": r[3],
                "Duration": r[4],
                "Active": r[5],
                "ConsentID": r[6]
            }
            for r in response
        ]
    return json.dumps(insuranceConsents)

async def validateReceiver(address: str, role):
    registered = await dataSC.functions.isUserRegistered(address).call()
    userRole = await dataSC.functions.getUserRole(address).call()
    if (registered and (userRole == role)):
        return "Receiver validated successfully"
    elif not registered:
        return "Receiver is invalid because it is not registered"
    elif (userRole != role):
        return f"Receiver is invalid because you are assuming the receiver is a {role}, but but it is actually a {userRole}"