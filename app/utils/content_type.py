from mimetypes import guess_type


def get_content_type(filename: str) -> str | None:
    """
    Return a MIME content-type for the provided filename.
    Falls back to 'application/octet-stream' when unknown.
    """
    content_type, _ = guess_type(filename)
    return content_type or "application/octet-stream"
