# LLMs for Privacy-Preserving and Regulation-Aware Healthcare Data Sharing

This repository contains the full implementation of the agentic LLM framework and blockchain-based consent management system described in the paper *“Agentic LLMs and Blockchain for Ensuring Regulatory Compliance and Privacy in Cross-Border Healthcare Data Sharing.”* 
It includes all system components, smart contracts, and evaluation scripts required to run the framework and reproduce the experiments.

---

## 📁 Repository Structure

```
├── System Code/
│   ├── orchestrator.py
│   ├── regulatoryComplianceAgent.py
│   ├── consentVerificationAgent.py
│   └── dataFilteringAgent.py
│
├── Smart Contracts/
│   ├── ConsentManager.sol
│   └── DataExchange.sol
│
├── Evaluation/
│   ├── orchestratorInputExtractionEval.py
│   ├── orchestratorSystemLevelEval.py
│   ├── regulationAgentEval.py
│   ├── consentAgentEval.py
│   └── filteringAgentEval.py
│
└── Evaluation Results/
    ├── Orchestrator Evaluation Results.csv
    ├── Orchestrator System-Level Results.csv
    ├── Regulation Agent Evaluation.csv
    ├── Consent Agent Evaluation.csv
    └── Filtering Agent Evaluation.csv
```

---

## 🔧 Environment Setup

This project requires:

- Python 3.9+
- Install dependencies manually:

```
pip install openai anthropic langchain faiss-cpu web3 ipfshttpclient python-dotenv google-generativeai transformers accelerate
```

These cover LLM APIs, retrieval, blockchain interactions, and local LLM support.

---

## 🔑 Environment Variables

Create a `.env` file:

```
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
GOOGLE_API_KEY=your_gemini_key
INFURA_API_KEY=your_infura_project_id
ETH_PRIVATE_KEY=your_sepolia_private_key
```

Used for:

- LLM access  
- Infura + Sepolia blockchain connections  
- Signing transactions  

---

## 🧱 Deploying Smart Contracts (Sepolia)

Using **Remix**:

1. Open https://remix.ethereum.org  
2. Upload smart contract files  
3. Connect MetaMask to Sepolia  
4. Deploy `ConsentManager.sol` and `DataExchange.sol`  
5. Copy deployed contract addresses into system code  

---

## ▶️ Running the System

Run the orchestrator:

```
python "System Code/orchestrator.py"
```

The orchestrator will:

- Parse the request  
- Run regulatory + consent agents  
- Run data filtering when required  
- Interact with smart contracts  
- Produce execution route + tool calls  

---

## 📊 Reproducing Evaluation Results

Run each script in `/Evaluation`:

```
python Evaluation/orchestratorInputExtractionEval.py
python Evaluation/regulationAgentEval.py
python Evaluation/consentAgentEval.py
python Evaluation/filteringAgentEval.py
python Evaluation/orchestratorSystemLevelEval.py
```

Outputs are saved in **Evaluation Results/**.

---

## 📁 Dataset Structure Used in Evaluations

### Orchestrator (Agent-Level)
Synthetic requests with:

- Countries  
- Roles  
- Purposes  
- Addresses  
- Missing fields  

### Regulatory Compliance Dataset
Country pairs referencing **real regulation excerpts** from GDPR, HIPAA, UAE, UK, Germany.

Ground-truth includes:

- consent requirements  
- anonymization rules  
- allowed data types  

### Consent Verification Dataset
Each object includes:

- data types  
- purposes  
- anonymization requirement  
- receiver attributes  
- validity window  

### Data Filtering Dataset
Each synthetic patient file includes:

- PHI  
- clinical fields  
- allowed data categories  
- anonymization rules  

### System-Level Orchestrator Dataset
Each scenario contains:

- full natural-language request  
- sender/receiver details  
- purpose of sharing  
- blockchain addresses  
- regulatory/consent context  
- partial, conflicting, or complete information  

The orchestrator must:

- determine the **ordered execution route**  
- select **tool calls**  
- decide whether to ask **human-in-the-loop** questions  

---

## 📎 Notes

- PHI processing is performed **locally**  
- Blockchain ensures **auditability** and **consent enforcement**  
- Local and API-based LLMs are supported  

---

