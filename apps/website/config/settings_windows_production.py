import os


os.environ["RUNTIME_STATE_BACKEND"] = "database"

from .settings_production import *  # noqa: E402,F403
