"""
ingestion/gdrive_connector.py

Pulls documents from Google Drive using the Google Drive API.
Supports: Google Docs (exported as plain text), .txt, .md, and PDF files.

SETUP (one time only):
1. Go to console.cloud.google.com
2. Create a new project (or use existing)
3. Enable "Google Drive API"
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
5. Choose "Desktop App", download the JSON, save as credentials.json in project root
6. First run will open a browser to authenticate — after that it's automatic

Why OAuth and not an API key?
Because we're reading YOUR Drive, not public data.
OAuth proves to Google that you own the account.
"""
import os
import io
import json
from pathlib import Path
from ingestion.chunker import chunk_text, Chunk

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def _get_drive_service():
    """
    Authenticate and return a Google Drive service object.
    First run: opens browser for OAuth consent.
    After that: uses saved token.json automatically.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        raise ImportError(
            "Google Drive packages not installed.\n"
            "Run: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib"
        )

    creds = None

    # Load saved token if it exists
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # If no valid token, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"credentials.json not found.\n"
                    f"Download it from Google Cloud Console and place it in: {os.getcwd()}"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for next time
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    from googleapiclient.discovery import build
    return build("drive", "v3", credentials=creds)


def _export_google_doc(service, file_id: str) -> str:
    """Export a Google Doc as plain text."""
    from googleapiclient.http import MediaIoBaseDownload
    request = service.files().export_media(
        fileId=file_id,
        mimeType="text/plain"
    )
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue().decode("utf-8", errors="ignore")


def _download_file(service, file_id: str) -> str:
    """Download a plain file (.txt, .md) as text."""
    from googleapiclient.http import MediaIoBaseDownload
    request = service.files().get_media(fileId=file_id)
    buffer = io.BytesIO()
    downloader = MediaIoBaseDownload(buffer, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buffer.getvalue().decode("utf-8", errors="ignore")


def ingest_gdrive_folder(
    folder_id: str,
    max_files: int = 50,
) -> list[Chunk]:
    """
    Ingest all supported documents from a Google Drive folder.

    Args:
        folder_id: The ID from the Drive folder URL
                   e.g. drive.google.com/drive/folders/THIS_PART
        max_files: safety limit

    Returns:
        List of Chunk objects ready for the vector store
    """
    service = _get_drive_service()

    # Supported MIME types
    supported = {
        "application/vnd.google-apps.document": "gdoc",
        "text/plain": "text",
        "text/markdown": "markdown",
    }

    # List files in folder
    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(
        q=query,
        pageSize=max_files,
        fields="files(id, name, mimeType, modifiedTime, owners)",
    ).execute()

    files = results.get("files", [])
    all_chunks = []

    for f in files:
        mime = f.get("mimeType", "")
        name = f.get("name", "unknown")
        file_id = f["id"]
        modified = f.get("modifiedTime", "")[:10]
        owner = f.get("owners", [{}])[0].get("displayName", "")
        url = f"https://drive.google.com/file/d/{file_id}/view"

        if mime not in supported:
            print(f"  [gdrive] SKIP {name} (unsupported type: {mime})")
            continue

        try:
            if mime == "application/vnd.google-apps.document":
                text = _export_google_doc(service, file_id)
            else:
                text = _download_file(service, file_id)

            if not text.strip():
                print(f"  [gdrive] SKIP {name} (empty)")
                continue

            chunks = chunk_text(
                text=text,
                source_type="gdrive",
                source_name=name,
                source_url=url,
                author=owner,
                date=modified,
            )
            all_chunks.extend(chunks)
            print(f"  [gdrive] {name} → {len(chunks)} chunks")

        except Exception as e:
            print(f"  [gdrive] ERROR {name}: {e}")

    print(f"  [gdrive] total: {len(files)} files, {len(all_chunks)} chunks")
    return all_chunks


def ingest_gdrive_file(file_id: str, file_name: str = "") -> list[Chunk]:
    """Ingest a single Google Drive file by its ID."""
    service = _get_drive_service()

    meta = service.files().get(
        fileId=file_id,
        fields="name, mimeType, modifiedTime, owners"
    ).execute()

    name = file_name or meta.get("name", file_id)
    mime = meta.get("mimeType", "")
    modified = meta.get("modifiedTime", "")[:10]
    owner = meta.get("owners", [{}])[0].get("displayName", "")
    url = f"https://drive.google.com/file/d/{file_id}/view"

    if mime == "application/vnd.google-apps.document":
        text = _export_google_doc(service, file_id)
    else:
        text = _download_file(service, file_id)

    return chunk_text(
        text=text,
        source_type="gdrive",
        source_name=name,
        source_url=url,
        author=owner,
        date=modified,
    )
