import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
SCENARIO_FILE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "demo_scenarios", "gmail_crm_slack.json"
)
