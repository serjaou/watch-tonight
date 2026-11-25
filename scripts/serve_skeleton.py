"""Serve part 1 of the walking skeleton locally, with in-memory adapters.

Run `uv run poe serve`, then open http://127.0.0.1:8000/docs (FastAPI's Swagger UI) and
try `POST /search` with, for example:

    {"text": "Something light for tonight", "country": "ES", "providers": [8, 337]}

The catalogue is the fictional fixture films of the acceptance tests; the LLM and the
embedder are deterministic fakes, so nothing is called over the network and nothing costs.
"""

from tests.acceptance.walking_skeleton_fixtures import FILMS

from watch_tonight.api.app import create_app
from watch_tonight.application.search_movies import SearchMovies
from watch_tonight.infra.fakes import EchoLanguageModel, HashEmbedder
from watch_tonight.infra.memory import InMemoryCatalogue

app = create_app(SearchMovies(EchoLanguageModel(), HashEmbedder(), InMemoryCatalogue(FILMS)))
