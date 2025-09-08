import streamlit as st
from openai import OpenAI
import os


# Set up your API key
os.environ["OPENAI_API_KEY"] = ""
SHARING_ASSISTANT_ID = ""

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


async def run_data_filtering_agent(user_input: str, file_path: str, output_path: str, threadId: str):
    # Step 1: Read patient data from file as plain text
    st.markdown(
        '<span style="font-size:14px;">📂 Reading uploaded patient data...</span>',
        unsafe_allow_html=True
    )
    st.session_state.chat_history.append({
        "role": "status",
        "agent": "Data Filtering Agent",
        "label": "✓ 📝 Data Filtering Agent analysis completed!",
        "details": (
            "📂 Reading uploaded patient data..."
        )
    })
    with open(file_path, 'r', encoding='utf-8') as file:
        patient_data_text = file.read()

    # Step 2: Add user messages
    client.beta.threads.messages.create(
        thread_id=threadId,
        role="user",
        content=f"These are the data sharing requirements:\n{user_input}"
    )
    
    client.beta.threads.messages.create(
        thread_id=threadId,
        role="user",
        content=f"This is the patient data:\n{patient_data_text}"
    )

    # Step 3: Run the assistant on the thread
    st.markdown(
        '<span style="font-size:14px;">⚙️ Filtering out restricted fields and applying anonymization...</span>',
        unsafe_allow_html=True
    )
    for chat in st.session_state.chat_history:
        if chat["role"] == "status" and chat["agent"] == "Data Filtering Agent":
            chat["details"] += "\n ⚙️ Filtering out restricted fields and applying anonymization..."
            break
    run = client.beta.threads.runs.create(
        thread_id=threadId, 
        assistant_id=SHARING_ASSISTANT_ID)

    # Step 4: Wait for run completion
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=threadId, run_id=run.id)
        if (run.status == "completed"):
            messages = client.beta.threads.messages.list(thread_id=threadId)
            if (messages.data and messages.data[0].role == "assistant" and len(messages.data[0].content) > 0):
                llmResponse = messages.data[0].content[0].text.value
                
                st.markdown(
                    '<span style="font-size:14px;">📂 Saving filtered data to new file...</span>',
                    unsafe_allow_html=True
                )
                for chat in st.session_state.chat_history:
                    if chat["role"] == "status" and chat["agent"] == "Data Filtering Agent":
                        chat["details"] += "\n 📂 Saving filtered data to new file..."
                        break
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(llmResponse)
                print(f"✅ Filtered file saved to: {output_path}")
                break
                
    return "✅ Data Filtered Successfully"

async def run_data_filtering_agent2(user_input: str, output_path: str, threadId: str):

    # Step 2: Add user messages
    client.beta.threads.messages.create(
        thread_id=threadId,
        role="user",
        content=user_input
    )

    # Step 3: Run the assistant on the thread
    run = client.beta.threads.runs.create(
        thread_id=threadId, 
        assistant_id=SHARING_ASSISTANT_ID)

    # Step 4: Wait for run completion
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=threadId, run_id=run.id)
        if (run.status == "completed"):
            messages = client.beta.threads.messages.list(thread_id=threadId)
            if (messages.data and messages.data[0].role == "assistant" and len(messages.data[0].content) > 0):
                llmResponse = messages.data[0].content[0].text.value
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(llmResponse)
                print(f"✅ Filtered file saved to: {output_path}")
                break
                    
    return "✅ Data Filtered Again Successfully"

async def run_data_filtering_agent3(user_input: str, file_path: str, threadId: str):
    # Step 1: Read patient data from file as plain text
    with open(file_path, 'r', encoding='utf-8') as file:
        patient_data_text = file.read()

    # Step 2: Add user messages
    client.beta.threads.messages.create(
        thread_id=threadId,
        role="user",
        content=f"These are the data sharing requirements:\n{user_input}"
    )
    
    client.beta.threads.messages.create(
        thread_id=threadId,
        role="user",
        content=f"This is the patient data:\n{patient_data_text}"
    )

    # Step 3: Run the assistant on the thread
    run = client.beta.threads.runs.create(
        thread_id=threadId, 
        assistant_id=SHARING_ASSISTANT_ID)

    # Step 4: Wait for run completion
    while True:
        run = client.beta.threads.runs.retrieve(thread_id=threadId, run_id=run.id)
        if (run.status == "completed"):
            messages = client.beta.threads.messages.list(thread_id=threadId)
            if (messages.data and messages.data[0].role == "assistant" and len(messages.data[0].content) > 0):
                llmResponse = messages.data[0].content[0].text.value
                return llmResponse