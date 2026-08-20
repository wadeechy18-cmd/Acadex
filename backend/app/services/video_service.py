from app.core.config import get_settings
from app.models.content import Video, VideoProvider
from app.storage.base import get_storage_backend


def resolve_playback_url(video: Video) -> str | None:
    """Turns stored video metadata into a URL the frontend can hand to a <video>
    or embed player, without the frontend ever needing to know which provider is
    in use. Only providers with a real integration return a URL; others are
    modeled (see docs/DATABASE_SCHEMA.md) but not wired up yet.
    """
    if video.provider == VideoProvider.YOUTUBE_UNLISTED and video.external_id:
        return f"https://www.youtube-nocookie.com/embed/{video.external_id}"

    if video.provider == VideoProvider.LOCAL and video.storage_key:
        if video.storage_key.startswith("http://") or video.storage_key.startswith("https://"):
            return video.storage_key
        settings = get_settings()
        return get_storage_backend().url_for(video.storage_key) if settings.storage_backend == "local" else None

    return None
