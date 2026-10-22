"""Launch the local web MVP: python -m services.web."""

import argparse
import logging
import os
from pathlib import Path

from services.llm.openai import ModelError, OpenAISettings, load_local_environment

from .application import Application
from .server import ROOT, ReviewServer


def main():
    parser = argparse.ArgumentParser(description="Run Material Continuity local synthetic web MVP")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--database", type=Path, default=ROOT / "data" / "local" / "review.sqlite3")
    args = parser.parse_args()
    try:
        load_local_environment(ROOT)
        settings = OpenAISettings.from_environment()
    except ModelError:
        parser.error("Invalid LLM configuration. Check provider/model and numeric limits; no secret values are logged.")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    app = Application(
        args.database, ROOT / "data" / "fixtures", ROOT / "data" / "documents",
        demo_password=os.environ.get("MATERIAL_CONTINUITY_DEMO_PASSWORD", "local-demo"),
        llm_settings=settings,
    )
    server = ReviewServer(("127.0.0.1", args.port), app)
    print(f"Material Continuity: http://127.0.0.1:{server.server_port}", flush=True)
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
