"""Configuration check without network traffic: python -m services.llm."""

import json
from pathlib import Path
import sys

from .openai import ModelError, OpenAISettings, load_local_environment
from .sap_ai_core import SAPAICoreSettings


def main():
    try:
        load_local_environment(Path(__file__).resolve().parents[2])
        provider = __import__("os").environ.get("MATERIAL_CONTINUITY_LLM_PROVIDER", "fixtures")
        status = (SAPAICoreSettings.from_environment().status()
                  if provider == "sap_ai_core" else OpenAISettings.from_environment().status())
    except ModelError as error:
        print(json.dumps({"error": error.code}))
        return 1
    print(json.dumps(status, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
