📦 PC Transfer Optimizer

An AI-powered PC Transfer Optimizer built using n8n, FastAPI, Google Gemini AI, Google OR-Tools, and Google Sheets. The system automates employee transfer processing by extracting information from uploaded PDFs, optimizing PC allocation, detecting employee swap cycles, minimizing unnecessary shipments, and generating reports.

🚀 Project Overview

The PC Transfer Optimizer helps organizations automatically optimize PC movement during employee transfers.

Instead of manually checking transfers and inventory, the system:

📄 Reads Employee Transfer PDF
📄 Reads PC Inventory PDF
🤖 Uses AI to extract structured JSON
🔄 Detects 2-way and 3-way employee swaps
🚚 Calculates only required PC shipments
📊 Stores results into Google Sheets
🌐 Displays optimization results on a web interface
🏗️ Architecture
HTML Frontend
      │
      ▼
Upload Employee & Inventory PDFs
      │
      ▼
n8n Webhook
      │
      ▼
Split Large PDFs
      │
      ▼
Extract PDF Text
      │
      ▼
Google Gemini AI
      │
      ▼
Parse JSON
      │
      ▼
Prepare Optimization Request
      │
      ▼
FastAPI Backend
      │
      ▼
Google OR-Tools
      │
      ▼
Transfer Optimization
      │
      ▼
Google Sheets
      │
      ▼
Respond to Webhook
      │
      ▼
HTML Frontend Displays Result
⚙️ Workflow Steps
1️⃣ HTML Frontend

Created a responsive web interface where users can:

📄 Upload Employee Transfer PDF
📄 Upload Asset Inventory PDF
📊 Upload Distance Matrix (Excel)
💬 Ask AI questions
📥 Download optimization report
2️⃣ Webhook (n8n)

Created an n8n Webhook to receive uploaded files from the HTML frontend.

Responsibilities:

Receive multipart form data
Trigger automation workflow
3️⃣ Split Upload Node

Separated uploaded files into:

Employee PDF
Inventory PDF
Distance Matrix
4️⃣ PDF Extraction

Extracted text from uploaded PDFs using PDF extraction nodes.

Extracted:

Employee Name
Employee ID
Current Location
New Location
Department
Inventory Information
5️⃣ Google Gemini AI

Used Google Gemini to convert extracted text into structured JSON.

Example:

{
  "employee_name":"Rahul Sharma",
  "employee_id":"EMP001",
  "from_location":"Mumbai",
  "to_location":"Delhi"
}
6️⃣ Parse JSON

Converted AI response into valid JSON format for backend processing.

7️⃣ Prepare Request

Prepared optimization payload matching FastAPI models.

Example:

{
  "transfers":[
    {
      "employee_id":"EMP001",
      "employee_name":"Rahul Sharma",
      "from_location":"Mumbai",
      "to_location":"Delhi"
    }
  ]
}
8️⃣ FastAPI Backend

Developed backend APIs using FastAPI.

Responsibilities:

Validate requests using Pydantic
Process transfer data
Call optimization engine
Return optimization results
9️⃣ Pydantic Models

Created request and response models.

Included:

Transfer
OptimizeRequest
CycleResolution
ShipmentResolution
OptimizeApiResponse
🔟 Google OR-Tools Optimization

Implemented optimization logic using Google OR-Tools.

Features:

Detect 2-way swaps
Detect 3-way swaps
Remove unnecessary shipments
Aggregate surplus transfers
Minimize logistics cost
1️⃣1️⃣ Cycle Detection

Implemented preprocessing algorithm to identify employee swap cycles.

Example:

Delhi → Mumbai

Mumbai → Delhi

becomes

2-Way Swap

No shipment required.

1️⃣2️⃣ Shipment Optimization

Generated optimized shipment routes for remaining unresolved transfers.

Example:

Kolkata → Hyderabad

Quantity = 1
1️⃣3️⃣ Google Sheets Integration

Automatically stored optimization results.

Columns:

SN
Employee No.
Employee Name
Grade
Current Location
New Location
New Function
Remarks
Swap Reason
Status
Surplus Transfer
Unresolved Transfer
Total Shipments Saved
Message
1️⃣4️⃣ Respond to Webhook

Returned optimization results back to the frontend in JSON format.

1️⃣5️⃣ HTML Result Display

Displayed:

✅ Swap Details
🚚 Shipment Routes
❌ Unresolved Transfers
📦 Shipments Saved
📋 Optimization Summary
🛠 Technologies Used
Tool	Purpose
🐍 Python	Backend Development
⚡ FastAPI	REST API
📦 Pydantic v2	Data Validation
🤖 Google Gemini AI	PDF Information Extraction
🔄 n8n	Workflow Automation
📄 PDF Extract Node	Text Extraction
🧠 JavaScript	n8n Code Nodes
📊 Google Sheets	Report Storage
🚚 Google OR-Tools	Optimization Solver
🌐 HTML	User Interface
🎨 CSS	Styling
⚙ JavaScript	Frontend Logic
📁 GitHub	Version Control
✨ Key Features
📄 Upload Employee Transfer PDF
📄 Upload Inventory PDF
🤖 AI-powered JSON extraction
🔄 Automatic 2-way swap detection
🔁 Automatic 3-way swap detection
🚚 Shipment optimization
📊 Google Sheets integration
📥 Download optimization report
🌐 Interactive web dashboard
⚡ Fully automated n8n workflow
📂 Project Structure
PC-Transfer-Optimizer/
│
├── app/
│   ├── api/
│   ├── models/
│   ├── optimizer/
│   ├── parser/
│   ├── services/
│   ├── utils/
│   └── main.py
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── script.js
│
├── n8n-workflow/
│
├── requirements.txt
│
└── README.md
📈 Workflow Summary
📄 Upload PDFs
        │
        ▼
Webhook
        │
        ▼
Split Upload
        │
        ▼
Extract PDF Text
        │
        ▼
Google Gemini AI
        │
        ▼
Parse JSON
        │
        ▼
Prepare Request
        │
        ▼
FastAPI Backend
        │
        ▼
Google OR-Tools
        │
        ▼
Detect Swaps
        │
        ▼
Optimize Shipments
        │
        ▼
Google Sheets
        │
        ▼
Respond to Webhook
        │
        ▼
HTML Dashboard
🎯 Outcome

The PC Transfer Optimizer automates the complete logistics optimization workflow by combining AI-based document extraction, optimization algorithms, workflow automation, and reporting. It reduces manual effort, minimizes unnecessary PC shipments through swap detection, provides optimized transfer recommendations, and stores the results in Google Sheets while presenting them through a user-friendly HTML dashboard.
