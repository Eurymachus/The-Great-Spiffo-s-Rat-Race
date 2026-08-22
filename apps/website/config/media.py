import mimetypes
from pathlib import Path, PurePosixPath

from asgiref.sync import sync_to_async
from django.conf import settings
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.utils.http import http_date
from django.views.decorators.http import require_http_methods


MEDIA_CACHE_SECONDS = 3600
FILE_CHUNK_SIZE = 64 * 1024


def _resolved_media_file(media_path):
    if not media_path or "\\" in media_path:
        raise Http404
    relative = PurePosixPath(media_path)
    if relative.is_absolute() or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise Http404

    try:
        root = Path(settings.MEDIA_ROOT).resolve(strict=True)
        candidate = root.joinpath(*relative.parts).resolve(strict=True)
    except (OSError, RuntimeError):
        raise Http404 from None
    if not candidate.is_relative_to(root) or not candidate.is_file():
        raise Http404
    return candidate


async def _file_chunks(path):
    file_handle = await sync_to_async(path.open, thread_sensitive=False)("rb")
    try:
        while chunk := await sync_to_async(
            file_handle.read, thread_sensitive=False
        )(FILE_CHUNK_SIZE):
            yield chunk
    finally:
        await sync_to_async(file_handle.close, thread_sensitive=False)()


def _apply_media_headers(response, stat):
    response["Content-Length"] = str(stat.st_size)
    response["Last-Modified"] = http_date(stat.st_mtime)
    response["Cache-Control"] = f"public, max-age={MEDIA_CACHE_SECONDS}"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@require_http_methods(["GET", "HEAD"])
async def persistent_media(request, media_path):
    path = await sync_to_async(_resolved_media_file, thread_sensitive=False)(
        media_path
    )
    stat = await sync_to_async(path.stat, thread_sensitive=False)()
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if request.method == "HEAD":
        response = HttpResponse(content_type=content_type)
    else:
        response = StreamingHttpResponse(
            _file_chunks(path),
            content_type=content_type,
        )
    return _apply_media_headers(response, stat)
