# StudySloth 🦥
**Less Stress. More Learning.** A cloud-ready study assistant powered by open-weight AI.

StudySloth turns study material into a chapter summary, flashcards, multiple-choice quizzes, and a short revision plan.

## Features
- Upload a text-based PDF or paste notes.
- Generate a summary, flashcards, quiz questions, and revision tasks.
- Try a fully working demo mode without an API key.
- Connect a hosted OpenAI-compatible inference endpoint and an open-weight model.
- Download the summary as Markdown or the full pack as JSON.
- Quiz scoring and answer explanations.
- Streamlit interface with notes, flashcards, quizzes, revision plan, and settings.

## Requirements
- Python 3.10 or newer
- Internet access for installing dependencies and for live hosted inference
- An API key from a compatible hosted inference provider for live AI (demo mode does not require one)

## Run locally
```bash
# Windows
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

```bash
# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

The app opens in your browser, usually at `http://localhost:8501`.

## Use demo mode
Choose **Demo mode** in the sidebar. This uses included sample Machine Learning content and works without an API key.

## Connect a hosted open-weight model
1. Create an API key with a provider that supports the OpenAI Chat Completions API.
2. Choose an open-weight model available through that provider.
3. Open **Settings** in StudySloth.
4. Enter the provider's base URL, model ID, and API key.
5. Select **Live open-weight AI** in the sidebar.
6. Upload a PDF or paste study material and click **Generate revision pack**.

Default values are examples and may change as providers update their model catalog. If your provider uses another model ID or base URL, update the settings. The app appends `/chat/completions` to the base URL.

You can also set environment variables:
```bash
API_KEY=your_key
BASE_URL=https://api.groq.com/openai/v1
MODEL=your-provider-supported-open-weight-model
```
Do not commit real API keys. For deployment, store secrets in your host's secret manager/environment configuration rather than in source code.

## Deploy
StudySloth is a Streamlit app and can be deployed on a Python-compatible host such as Streamlit Community Cloud or another container/PaaS host.

For Streamlit Community Cloud:
1. Push this folder to a GitHub repository.
2. Create a new app in Streamlit Community Cloud and select `app.py`.
3. Add `API_KEY`, `BASE_URL`, and `MODEL` under app secrets if you want live inference.
4. Deploy. Demo mode works without a key.

**Security note:** In this prototype, keys entered in Settings are stored in the current Streamlit session state. For a public multi-user deployment, prefer server-side environment secrets and avoid collecting users' provider keys. Add authentication and rate limiting before opening the app broadly.

## Open innovation and the hackathon
StudySloth uses an open-weight model as the core text-generation engine while allowing the model/provider to be changed through configuration. The hosted approach means users do not need to install model weights or own a GPU. This trades offline operation for easier access. In live mode, submitted study text is sent to the configured inference provider; do not claim fully local processing. Review the chosen model license and provider's privacy terms before submission.

Suggested hackathon demo:
1. Open the dashboard in Demo mode and show the interface.
2. Upload a text-based PDF or paste a chapter.
3. Generate the revision pack in Live mode using an open-weight model.
4. Show the summary, flashcards, quiz scoring, and revision checklist.
5. Explain that the model can be swapped and that no proprietary model API is required when using a compatible open-weight model provider.

## Limitations
- PDF extraction supports selectable text; scanned PDFs require OCR.
- Very large documents are truncated before model submission; split chapters for better results.
- Model output can be incorrect. Review summaries and answers before studying.
- Provider availability, pricing, rate limits, and model IDs can change.
- This is a prototype, not a production-grade multi-user service.

## License
MIT for this application code. This license does not apply to the separately selected AI model or inference provider; review their licenses and terms.
