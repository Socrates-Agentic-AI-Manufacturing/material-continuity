"""Launch the local web MVP: python -m services.web."""

import argparse
import logging
import os
from pathlib import Path

from services.llm.openai import ModelError, OpenAIResponsesClient, OpenAISettings, load_local_environment
from services.llm.sap_ai_core import SAPAICoreClient, SAPAICoreSettings

from .application import Application
from .server import ROOT, ReviewServer


def main():
    parser = argparse.ArgumentParser(description="Run Material Continuity local synthetic web MVP")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "local" / "review.sqlite3")
    args = parser.parse_args()
    try:
        load_local_environment(ROOT)
        provider = os.environ.get("MATERIAL_CONTINUITY_LLM_PROVIDER", "fixtures")
        if provider == "sap_ai_core":
            settings = SAPAICoreSettings.from_environment()
            llm_client = SAPAICoreClient(settings)
        else:
            settings = OpenAISettings.from_environment()
            llm_client = OpenAIResponsesClient(settings)
    except ModelError:
        parser.error("Invalid LLM configuration. Check provider/model and numeric limits; no secret values are logged.")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    app = Application(
        args.database, ROOT / "data" / "fixtures", ROOT / "data" / "documents",
        demo_password=os.environ.get("MATERIAL_CONTINUITY_DEMO_PASSWORD", "local-demo"),
        llm_settings=settings,
        llm_client=llm_client,
    )
    configured_hosts = tuple(
        item.strip() for item in os.environ.get("MATERIAL_CONTINUITY_ALLOWED_HOSTS", "").split(",")
        if item.strip()
    )
    server = ReviewServer((args.host, args.port), app, allowed_hosts=configured_hosts)
    print(f"Material Continuity: http://{args.host}:{server.server_port}", flush=True)
    print("Local synthetic demo. Users: engineering, quality, planner. See README for login.", flush=True)
    print(f"LLM provider: {settings.provider}; configured: {settings.status()['configured']}. No automatic API calls.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
