# WorkFlowOS — AI-Powered Workflow Automation Agent

WorkFlowOS is an AI-powered workflow automation system that learns from repetitive user activity.

Instead of requiring a user to manually design an automation, WorkFlowOS follows the flow:

**Observe → Detect Repetition → Understand Intent → Generate Workflow → User Approval → Automate → Record Results**

The system observes application activity, identifies repeated multi-step patterns, converts the pattern into a structured workflow, asks for user approval, and executes the approved workflow.

---

## 🎯 Problem

People repeatedly perform the same sequence of actions across different applications:

**Open Email → Download Attachment → Update CRM → Notify Team**

Traditional automation tools generally require the user to understand the process first and manually create the automation.

WorkFlowOS approaches the problem differently:

> **The system observes what the user already does and proposes the automation for them.**

---

# 🔄 Core Workflow

```text
┌─────────────────────┐
│   Observe Activity  │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Detect Repetition   │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Understand Intent   │
│       (AI)          │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Generate Structured │
│     Workflow        │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│  User Approval      │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Execute Automation  │
└──────────┬──────────┘
           ↓
┌─────────────────────┐
│ Record Results &    │
│ Execution History   │
└─────────────────────┘
```

---

# 🚀 Demonstration Workflow

The current MVP demonstrates the following repeated workflow:

```text
Gmail
   ↓
Download Attachment
   ↓
HubSpot CRM
   ↓
Slack
```

The demo activity stream contains multiple repetitions of this sequence.

WorkFlowOS detects:

- **4 steps**
- **4 applications**
- **3 occurrences**
- **95% confidence**

It then generates the workflow:

> **Process Customer Invoice Attachment**

The user reviews and approves the proposed automation before execution.

---

# 🧠 How It Works

## 1. Observe

WorkFlowOS receives structured desktop activity events representing actions performed by a user.

Example:

```text
Gmail → open_email
Browser Download → download_file
HubSpot CRM → update_customer_record
Slack → send_message
```

The MVP includes a realistic demo event stream so that the complete workflow can be demonstrated reliably.

---

## 2. Detect Repetition

The repetition detector analyzes the event stream and searches for repeated multi-step sequences.

For the demonstration scenario it identifies:

```text
Gmail: Open Email
        ↓
Browser Download: Download File
        ↓
HubSpot CRM: Update Customer Record
        ↓
Slack: Send Message
```

The detector reports:

```text
Occurrences: 3
Confidence: 95%
Applications: 4
```

A single occurrence is not treated as a repeated workflow.

---

## 3. Understand Intent

The detected sequence is passed to the workflow understanding engine.

The system can use the Google Gemini API through the `google-genai` SDK to interpret the sequence and generate a structured workflow.

The AI layer is designed to infer:

- Workflow name
- User intent
- Trigger condition
- Application actions
- Parameters
- Workflow step order

---

## 4. Generate Structured Workflow

The workflow is represented using validated Pydantic models.

Example generated workflow:

```text
Process Customer Invoice Attachment

Trigger:
New email with an attachment from a known customer/vendor domain

Step 1:
Gmail → Open Email

Step 2:
Browser Download → Download File

Step 3:
HubSpot CRM → Update Customer Record

Step 4:
Slack → Send Message
```

The generated parameters are represented using placeholders such as:

```text
{{customer_id}}
{{attachment_path}}
{{invoice_id}}
{{customer_name}}
```

This allows the workflow to be parameterized rather than tied to a single event.

---

# 👤 Human Approval

WorkFlowOS does not automatically activate a newly generated workflow.

The dashboard presents the generated workflow to the user first.

The user can review:

- Workflow intent
- Trigger
- Steps
- Applications
- Parameters
- Estimated time saved

The workflow initially has the state:

```text
PENDING_APPROVAL
```

After user approval:

```text
APPROVED
```

Only approved workflows can be executed.

This provides a human-in-the-loop safety mechanism.

---

# ⚡ Automation Engine

The MVP contains local workflow adapters representing:

- Gmail
- Browser Download
- HubSpot CRM
- Slack

For the hackathon demonstration these adapters are **simulated/local adapters** rather than live third-party API integrations.

This makes the demonstration deterministic and avoids requiring external service credentials.

Example execution:

```text
✓ Gmail: Open Email
✓ Browser Download: Download File
✓ HubSpot CRM: Update Customer Record
✓ Slack: Send Message
```

The execution engine records:

- Step status
- Execution duration
- Output summary
- Execution logs
- Total execution duration
- Estimated time saved
- Overall execution status

---

# 📊 Demonstrated Execution

A successful demonstration run produces:

```text
Status: SUCCESS

Steps Completed: 4/4

Execution Time: ~686 ms

Estimated Time Saved: 3 minutes
```

Each step also reports its individual execution duration and output.

---

# 🗂 Execution History

Completed workflow executions are recorded by the storage service.

The execution history contains:

- Execution ID
- Workflow ID
- Workflow name
- Overall status
- Individual step results
- Execution durations
- Logs
- Estimated time saved
- Execution timestamp

The current MVP uses in-memory storage for the demonstration.

---

# 🏗 Architecture

```text
React Dashboard
      │
      │ REST API
      ▼
FastAPI Backend
      │
      ├── Observer
      │      └── Activity Events
      │
      ├── Detector
      │      └── Repeated Sequence Detection
      │
      ├── LLM Engine
      │      └── Intent Understanding + Workflow Generation
      │
      ├── Workflow Engine
      │      └── Approval + Workflow Management
      │
      ├── Executor
      │      └── Workflow Step Execution
      │
      └── Storage
             └── Execution History
```

The data flow is:

```text
Activity Events
      ↓
Repetition Detection
      ↓
AI Workflow Understanding
      ↓
Structured Workflow
      ↓
User Approval
      ↓
Workflow Execution
      ↓
Execution History
```

---

# 🛠 Technology Stack

## Backend

- **Python 3.11**
- **FastAPI**
- **Uvicorn**
- **Pydantic**
- **Google GenAI SDK (`google-genai`)**
- Python standard library for workflow detection, execution, and storage

## Frontend

- **React**
- **Vite**
- Custom CSS
- REST API integration with the FastAPI backend

---

# 📂 Project Structure

```text
WorkFlowOS/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes_events.py
│   │   │   ├── routes_workflows.py
│   │   │   └── routes_execution.py
│   │   │
│   │   ├── models/
│   │   │   ├── event.py
│   │   │   └── workflow.py
│   │   │
│   │   ├── services/
│   │   │   ├── observer.py
│   │   │   ├── detector.py
│   │   │   ├── llm_engine.py
│   │   │   ├── executor.py
│   │   │   └── storage.py
│   │   │
│   │   ├── config.py
│   │   └── main.py
│   │
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
│
├── demo_scenarios/
│   └── gmail_crm_slack.json
│
└── README.md
```

---

# ⚙️ Installation

## Prerequisites

- Python 3.11+
- Node.js and npm

---

## 1. Open the project

```bash
cd WorkFlowOS
```

---

## 2. Install backend dependencies

```bash
pip install -r backend/requirements.txt
```

---

## 3. Start the backend

From the project root:

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

The API will be available at:

```text
http://127.0.0.1:8000
```

---

## 4. Install frontend dependencies

Open another terminal:

```bash
cd frontend
npm install
```

---

## 5. Start the frontend

```bash
npm run dev
```

Open:

```text
http://localhost:5173
```

---

# 🤖 Optional Gemini Configuration

The workflow generation engine supports Google Gemini through the `google-genai` SDK.

Set the environment variable:

```text
GEMINI_API_KEY=your_api_key
```

When a valid Gemini API key is available, the engine can use the Gemini generation path.

For reliability, the application also contains a deterministic workflow-generation fallback.

If the API key is missing or the Gemini request fails, WorkFlowOS falls back to the deterministic generator so that the complete hackathon demonstration remains functional.

---

# 🧪 Testing

The backend contains automated tests covering:

- Repetition detection
- Confidence scoring
- Empty event handling
- Single-occurrence handling
- Workflow generation
- Workflow schema validation
- Parameter generation
- API integration
- Gemini failure fallback
- Gemini API usage path

Run:

```bash
python -m unittest discover -s backend/tests -v
```

Current validation:

```text
Ran 24 tests
OK
```

---

# 🔌 API Flow

The main workflow API sequence is:

```text
GET  /api/workflows/detect
        ↓
POST /api/workflows/generate
        ↓
POST /api/workflows/{workflow_id}/approve
        ↓
POST /api/execution/run/{workflow_id}
        ↓
GET /api/execution/history
```

---

# 🎥 Demo Flow

The recommended demonstration sequence is:

### 1. Show the dashboard

```text
WorkFlowOS
AI-powered workflow automation
```

### 2. Show observed activity

```text
Gmail
 ↓
Download
 ↓
HubSpot CRM
 ↓
Slack
```

### 3. Show detection

```text
3 occurrences
95% confidence
4 applications
```

### 4. Show AI-generated workflow

```text
Process Customer Invoice Attachment
```

### 5. Approve

Click:

```text
APPROVE & AUTOMATE
```

### 6. Execute

Click:

```text
EXECUTE WORKFLOW
```

### 7. Show result

```text
SUCCESS
4/4 steps completed
~686 ms execution
3 min estimated time saved
```

This demonstrates the complete WorkFlowOS loop from observed activity to approved automation.

---

# 💡 Key Innovation

Traditional workflow automation generally starts with:

```text
User defines workflow
        ↓
User configures automation
        ↓
Automation executes
```

WorkFlowOS starts with the user's existing behavior:

```text
User works normally
        ↓
WorkFlowOS observes activity
        ↓
Repeated behavior is detected
        ↓
AI proposes the workflow
        ↓
User approves
        ↓
Workflow executes
```

The goal is to reduce the amount of manual workflow design required from the user.

---

# 🚧 Current MVP Scope

The current hackathon MVP focuses on proving the core intelligence loop:

- Structured activity observation
- Repetition detection
- AI-assisted workflow understanding
- Structured workflow generation
- Human approval
- Workflow execution
- Execution logging and history
- Dashboard visualization

The Gmail, Browser Download, HubSpot CRM, and Slack execution adapters are simulated/local adapters for the demonstration.

Future versions can connect the workflow engine to real application APIs, application integrations, accessibility-based UI control, browser automation, and computer-vision/UI fallbacks.

---

# 🏆 Hackathon Summary

**Project:** WorkFlowOS

**Core idea:** Automatically discover and automate repetitive desktop workflows using AI.

**Core principle:**

> Observe what users repeatedly do. Understand why they do it. Generate an automation. Ask for approval. Then automate it.
