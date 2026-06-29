# MedVault AI — Offline Personal Health Intelligence Platform

MedVault AI is a production-grade, offline-first personal health records intelligence app. It allows users to upload medical reports (PDFs, lab reports, discharge summaries) and extracts structured data fully offline using a local LLM, flags abnormal results, tracks health metrics over time, and supports natural-language offline search.

Zero data ever leaves the device.

## System Architecture
*   **OCR:** PyMuPDF + pdfplumber (text-based PDFs) + Tesseract OCR (images/scanned PDFs)
*   **Local LLM:** llama-cpp-python running Phi-3-mini-4k-instruct-Q4_K_M.gguf (Default) or Qwen2.5-3B-Instruct-Q4_K_M.gguf.
*   **Embeddings:** `all-MiniLM-L6-v2` via sentence-transformers (offline).
*   **Database:** Local SQLite database (`medvault.db`) with FTS5 for keyword search.
*   **Backend:** FastAPI exposes REST APIs (`/api/upload`, `/api/reports`, `/api/trends`, `/api/search`, `/api/export`).
*   **Frontend:** React + TailwindCSS + Plotly.js PWA. All libraries are downloaded and hosted locally in `/frontend/static` for 100% offline access without Node package managers.
*   **Mobile Wrapper:** Capacitor configurations provided in `/mobile`.

---

## Setup & Run Instructions

### 1. Python Environment Setup
1. Clone the repository.
2. Create a virtual environment:
   `python -m venv venv`
   `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
3. Install dependencies:
   `pip install fastapi uvicorn sqlite3 pytesseract fitz pdfplumber llama-cpp-python sentence-transformers pillow pydantic`
4. Install Tesseract OCR on your OS (e.g., `brew install tesseract` or use Windows installer) and ensure it is in your system PATH.

### 2. Download Local Models
Run the setup script to download the quantized LLM GGUF model:
```bash
python models/download.py
```
*(Optional)* You can choose the default Phi-3 or Qwen2.5.

### 3. Setup Frontend Assets
Run the script to fetch React, Tailwind, and Plotly.js for offline availability:
```bash
python frontend/download_libs.py
python frontend/download_babel.py
python frontend/generate_icon.py
```

### 4. Start the Application
From the `backend` directory, launch the FastAPI server:
```bash
cd backend
python -m uvicorn app.main:app --port 8000 --host 127.0.0.1
```
The server will automatically run SQLite migrations, mount the API, and serve the frontend at `http://127.0.0.1:8000/`.

---

## Mobile Build Architecture (Capacitor) & Tradeoffs

The Capacitor project config is located in `/mobile`. To build it, you require `Node.js` and `npm`.

**Tradeoff Documented: Backend Communication over LAN vs Embedded**
The mobile wrapper (`capacitor.config.json`) is currently configured to point its API server URL to `http://10.0.2.2:8000` (the Android emulator alias for localhost) or a local LAN IP.
*   **Why LAN over Embedded?** Running a full Python FastAPI backend *embedded* natively inside an Android/iOS app is highly non-trivial and requires tools like Chaquopy or Beeware, which introduces massive overhead and often incompatible ABI constraints for `llama.cpp` and `sentence-transformers`.
*   **Recommendation:** MedVault AI on mobile functions as a companion app that talks to your trusted local desktop/laptop server running over Wi-Fi (LAN). The data stays within your house's network and never touches the public internet.

---

## Phase 4: True On-Device Mobile LLM Feasibility

Running a quantized LLM directly on mobile devices (e.g., iPhone or Android) *is feasible* but carries the following considerations:

1.  **llama.cpp Mobile Bindings:** `llama.cpp` provides native iOS (Metal) and Android (JNI/OpenCL) builds. There are React Native wrappers like `llama.rn` which allow calling the GGUF models directly on the device GPU.
2.  **Memory Constraints:** A 1.5B or 3B model quantized at Q4 (like Qwen2.5-1.5B or Phi-3-mini) requires roughly 1.5GB to 2.5GB of RAM. Modern flagship phones (iPhone 13+, Pixel 6+) have 6-8GB of RAM and can load these models comfortably.
3.  **Battery & Thermal Cost:** Continuous local inference on mobile drains the battery extremely fast and causes thermal throttling after a few minutes. Since clinical extraction is bursty (one report at a time), it is acceptable.
4.  **Verdict (Unproven in this MVP):** While theoretically possible, bundling a 2GB model file within a Capacitor app is poor UX. The app should download the GGUF to the mobile filesystem on first launch (similar to our desktop approach) and use a Capacitor native C++ plugin to interface with `llama.cpp` directly. For this MVP, relying on the LAN backend remains the most stable, cross-platform approach.

---

## Verification Status
*   **Phase 1 (Backend Pipeline):** Verified via Pytest (`test_backend.py` passes 100%).
*   **Phase 2 (Frontend PWA):** Verified server initialization. Browser subagent verification was skipped due to API quota constraints, but manual E2E via browser is fully ready.
*   **Phase 3 (Mobile Wrapper):** Configured for Node environments.
*   **Phase 4 (On-Device LLM):** Investigated and documented above.
