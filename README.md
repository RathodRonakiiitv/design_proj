# ShieldCV 🛡️

**ShieldCV** is a quarantined two-stage pipeline for mitigating indirect prompt injection and hidden prompt exploits in LLM-assisted Resume/CV screening systems.

---

## 🌟 Key Features

- **Multi-Modal Hidden Text Detection**: Detects zero-point fonts, white-on-white text, font color match evasions, micro-fonts, and off-canvas text in PDFs and DOCX files.
- **Two-Stage Quarantined Pipeline**:
  - **Stage 1 (Extractor)**: Reads untrusted resume content in a strictly sandboxed prompt and produces a schema-validated, sanitised JSON profile.
  - **Stage 2 (Evaluator)**: Evaluates the candidate against job requirements using only the sanitised structured JSON, neutralizing injection payloads.
- **Multi-LLM Provider Support**: Supports NVIDIA NIM (Nemotron-3 / Llama-3), OpenAI (GPT-4o), and Google Gemini models.
- **Interactive Web Interface**: Complete client-side UI with real-time analysis, side-by-side comparison (Naive LLM vs. ShieldCV Pipeline), and injection telemetry.
- **Research & Benchmark Suite**: Includes automated benchmarks and LaTeX report generation (`main.tex`).

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10+
- Modern Web Browser

### 2. Backend Setup
1. Navigate to the `backend` folder and install dependencies:
   ```bash
   pip install fastapi uvicorn pydantic pypdf openai google-generativeai
   ```

2. Set up your environment variables:
   ```bash
   cp backend/.env.example backend/.env
   ```
   Add your NVIDIA NIM, OpenAI, or Google Gemini API key to `backend/.env`.

3. Start the backend server:
   ```bash
   python backend/server.py
   ```
   - API Docs: `http://localhost:8000/docs`
   - Health check: `http://localhost:8000/api/status`

### 3. Frontend Setup
Run the local HTTP server:
```bash
python serve.py
```
Open [http://localhost:3000](http://localhost:3000) (or the port specified in terminal) in your browser.

---

## 📁 Project Structure

```
├── backend/
│   ├── api.py                  # FastAPI routes and endpoints
│   ├── hidden_text_detector.py # PDF/DOCX hidden font & text extraction
│   ├── llm_providers.py        # LLM abstractions (NVIDIA, OpenAI, Gemini)
│   ├── pipeline.py             # Two-stage Quarantined Pipeline implementation
│   ├── run_benchmark.py        # Benchmark testing script
│   ├── schema.py               # Pydantic schemas for structured extraction
│   ├── server.py               # Backend entrypoint
│   └── test_pipeline.py        # Pipeline validation test
├── index.html                  # Web UI
├── styles.css                  # UI Design and themes
├── app.js                      # UI logic and API communication
├── serve.py                    # Static HTTP server for frontend
├── main.tex                    # Research paper / documentation
└── .gitignore                  # Git ignore rules
```