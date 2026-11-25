"""Serve the walking skeleton on local Atlas (part 2), with part 1's fake LLM and embedder.

    uv run poe db-up && uv run poe seed && uv run poe serve-atlas

Then open http://127.0.0.1:8000/docs. The database is `WATCH_TONIGHT_MONGODB_URI`
(default: the local container from compose.yaml).
"""

from watch_tonight.api.app import create_app
from watch_tonight.application.search_movies import SearchMovies
from watch_tonight.infra.fakes import EchoLanguageModel, HashEmbedder
from watch_tonight.infra.mongodb import MongoCatalogue, connect
from watch_tonight.infra.settings import Settings

settings = Settings()
client = connect(settings.mongodb_uri.get_secret_value())
catalogue = MongoCatalogue(client[settings.mongodb_database])
app = create_app(SearchMovies(EchoLanguageModel(), HashEmbedder(), catalogue, catalogue))
