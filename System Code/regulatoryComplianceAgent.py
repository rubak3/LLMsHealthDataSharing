import streamlit as st
from openai import OpenAI
import os
import json


# Set up your API key
os.environ["OPENAI_API_KEY"] = ""
REGULATION_ASSISTANT_ID = ""

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

async def run_regulation_agent(user_request: str, threadId: str):

    flag = False
    
    # Add user message
    client.beta.threads.messages.create(
        thread_id=threadId,
        role="user",
        content=user_request
    )

    # Run the Regulation Assistant
    run = client.beta.threads.runs.create(
        thread_id=threadId,
        assistant_id=REGULATION_ASSISTANT_ID,  # Replace with your actual assistant ID
    )
    
    # Poll until the assistant finishes
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=threadId,
            run_id=run.id
        )
        if run_status.status == "completed":
            if not flag:
                st.markdown(
                    '<span style="font-size:14px;">🧠 Interpretting and analyzing regulations to identify sharing requirements...</span>',
                    unsafe_allow_html=True
                )
                for chat in st.session_state.chat_history:
                    if chat["role"] == "status" and chat["agent"] == "Regulation Agent":
                        chat["details"] += "\n 🧠 Interpretting and analyzing regulations to identify sharing requirements..."
                        break
            # Retrieve assistant reply
            messages = client.beta.threads.messages.list(thread_id=threadId)
            regulationsAgentResponse = messages.data[0].content[0].text.value  # Plain text response
            print("\n📘 Final Regulation Interpretation:\n")
            print(regulationsAgentResponse)
            break
        elif run_status.status in ["failed", "cancelled", "expired"]:
            raise Exception(f"Assistant run failed with status: {run_status.status}")
        elif (run_status.status == "requires_action" and run_status.required_action.type == "submit_tool_outputs"):
            if (run_status.required_action.submit_tool_outputs.tool_calls[0].function.name == "search_web"):
                flag = True
                st.markdown(
                    '<span style="font-size:14px;">🔍 Not enough regulation data found locally. Searching the web for additional information...</span>',
                    unsafe_allow_html=True
                )
                for chat in st.session_state.chat_history:
                    if chat["role"] == "status" and chat["agent"] == "Regulation Agent":
                        chat["details"] += "\n 🔍 Not enough regulation data found locally. Searching the web for additional information..."
                        break
                callId = run_status.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run_status.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                print(arg["user_query"])
                output = await run_web_search_tool1(arg["user_query"])
                submitToolOutputs(output, run.thread_id, run.id, callId)

    return regulationsAgentResponse

async def run_regulation_agent2(user_request: str, threadId: str):

    # Add user message
    client.beta.threads.messages.create(
        thread_id=threadId,
        role="user",
        content=user_request
    )

    # Run the Regulation Assistant
    run = client.beta.threads.runs.create(
        thread_id=threadId,
        assistant_id=REGULATION_ASSISTANT_ID,  # Replace with your actual assistant ID
    )

    # Poll until the assistant finishes
    while True:
        run_status = client.beta.threads.runs.retrieve(
            thread_id=threadId,
            run_id=run.id
        )
        if run_status.status == "completed":
            # Retrieve assistant reply
            messages = client.beta.threads.messages.list(thread_id=threadId)
            regulationsAgentResponse = messages.data[0].content[0].text.value  # Plain text response
            print("\n📘 Final Regulation Interpretation:\n")
            print(regulationsAgentResponse)
            break
        elif run_status.status in ["failed", "cancelled", "expired"]:
            raise Exception(f"Assistant run failed with status: {run_status.status}")
        elif (run_status.status == "requires_action" and run_status.required_action.type == "submit_tool_outputs"):
            if (run_status.required_action.submit_tool_outputs.tool_calls[0].function.name == "search_web"):
                callId = run_status.required_action.submit_tool_outputs.tool_calls[0].id
                arg = json.loads(run_status.required_action.submit_tool_outputs.tool_calls[0].function.arguments)
                print(arg["user_query"])
                output = await run_web_search_tool1(arg["user_query"])
                submitToolOutputs(output, run.thread_id, run.id, callId)

    return regulationsAgentResponse

async def run_web_search_tool1(query: str):

    url_instruction = f"""
		You are a compliance assistant helping search for global healthcare data-sharing regulations.

		Please identify the official regulation documents for this case:

		\"\"\"{query}\"\"\"

		📌 Return a list of trusted, official webpages URLs for these documents (e.g., from .gov, .edu, official law websites) that will be used later to answer these questions based on the receiver and sender countries:
		- ✅ Can the data be shared?
		- ❌ What types of data are restricted?
		- 👤 Is patient consent required?
		- 🔐 Is anonymization required?
		- 🏛️ Is additional government approval required?

		If no enough official webpages found you can use unofficial sources.
		Do NOT provide summaries or any interpretation. 
		Return only a numbered list of URLs (not more than 10)!
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
        instructions=url_instruction,
        temperature=0,
    )
    print("\nURLs:\n")
    print(response2.output_text)

    return "URLs retrieved form the web: " + response2.output_text