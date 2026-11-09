import io
import zipfile


MAX_DOCUMENT_SIZE = 10 * 1024 * 1024

DOCUMENT_CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
}


def validate_document_content(file_name: str, content: bytes) -> str:
    extension = file_name.lower().rsplit(".", maxsplit=1)
    if len(extension) != 2 or f".{extension[1]}" not in DOCUMENT_CONTENT_TYPES:
        raise ValueError("File type is not allowed")
    suffix = f".{extension[1]}"
    if not content:
        raise ValueError("File must not be empty")
    if len(content) > MAX_DOCUMENT_SIZE:
        raise ValueError("File exceeds the 10 MB limit")

    if suffix == ".pdf" and not content.startswith(b"%PDF-"):
        raise ValueError("File content does not match its extension")
    if suffix in {".jpg", ".jpeg"} and not content.startswith(b"\xff\xd8\xff"):
        raise ValueError("File content does not match its extension")
    if suffix == ".png" and not content.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("File content does not match its extension")
    if suffix == ".doc" and not content.startswith(
        b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    ):
        raise ValueError("File content does not match its extension")
    if suffix == ".docx":
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                entries = set(archive.namelist())
        except zipfile.BadZipFile as exc:
            raise ValueError("File content does not match its extension") from exc
        if not {"[Content_Types].xml", "word/document.xml"}.issubset(entries):
            raise ValueError("File content does not match its extension")

    return suffix
