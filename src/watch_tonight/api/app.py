"""The HTTP API: `POST /search`, a thin adapter over `SearchMovies` (architecture §1).

`create_app` is the composition root: the caller passes a wired use case, and FastAPI's
`Depends` hands it to the endpoint (like constructor injection in ASP.NET Core).
"""

from collections.abc import Mapping
from typing import Annotated, Any, Final

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from watch_tonight.application.search_movies import SearchMovies
from watch_tonight.domain.errors import ServiceUnavailableError
from watch_tonight.domain.search import (
    FieldError,
    InvalidInputResponse,
    SearchRequest,
    SearchResponse,
    ServiceUnavailableResponse,
)

SERVICE_UNAVAILABLE_MESSAGE: Final[str] = (
    "The search is unavailable right now. Please try again later."
)


def _field_error(error: Mapping[str, Any]) -> FieldError:
    """One Pydantic error as `{field, message}`; `field` is the path inside the body."""
    location: tuple[object, ...] = tuple(error.get("loc", ()))
    in_a_field = location[:1] == ("body",) and len(location) > 1 and isinstance(location[1], str)
    # Unreadable JSON reports a character position, not a field: name the body then.
    path = [str(part) for part in location[1:]] if in_a_field else []
    message = str(error.get("msg", "Invalid value.")).removeprefix("Value error, ")
    return FieldError(field=".".join(path) or "body", message=message)


def create_app(search_movies: SearchMovies) -> FastAPI:
    app = FastAPI(title="watch-tonight", version="0.1.0")

    def get_search_movies() -> SearchMovies:
        return search_movies

    @app.exception_handler(RequestValidationError)
    async def invalid_input(request: Request, error: RequestValidationError) -> JSONResponse:
        # 422 rather than 400: the request was readable, but its values break a rule
        # (RFC 9110 §15.5.21). It's also FastAPI's default for validation errors.
        errors = [_field_error(e) for e in error.errors()]
        body = InvalidInputResponse(errors=errors)
        return JSONResponse(status_code=422, content=body.model_dump(mode="json"))

    @app.exception_handler(ServiceUnavailableError)
    async def service_unavailable(request: Request, error: ServiceUnavailableError) -> JSONResponse:
        body = ServiceUnavailableResponse(message=SERVICE_UNAVAILABLE_MESSAGE)
        return JSONResponse(status_code=503, content=body.model_dump(mode="json"))

    @app.post(
        "/search",
        response_model=SearchResponse,
        responses={
            422: {"model": InvalidInputResponse, "description": "Invalid input"},
            503: {"model": ServiceUnavailableResponse, "description": "Service unavailable"},
        },
    )
    async def search(
        request: SearchRequest,
        use_case: Annotated[SearchMovies, Depends(get_search_movies)],
    ) -> SearchResponse:
        """Five movies for a mood, streamable now on the selected services."""
        return await use_case.execute(request)

    return app
