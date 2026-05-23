"""
ingestion/github_connector.py

Pulls markdown files (READMEs, docs, wikis) from GitHub repos.
Uses the GitHub API via PyGitHub.

Without a token: 60 requests/hour (fine for a demo)
With a token:   5000 requests/hour

How it works:
1. Connect to GitHub (with or without token)
2. For each repo in your list, find all .md files
3. Download their content
4. Chunk and return
"""
from github import Github, GithubException
from ingestion.chunker import chunk_text, Chunk
from config import GITHUB_TOKEN


# Repos to ingest — publicly available automotive/embedded repos
# These are real repos with good documentation
DEFAULT_REPOS = [
    "linklayer/python-can",           # python CAN bus library
    "cantools/cantools",              # DBC file handling
    "libopencm3/libopencm3",         # embedded firmware library
    "micropython/micropython",        # embedded Python
    "zephyrproject-rtos/zephyr",     # RTOS used in automotive
]


def ingest_github_repo(
    repo_name: str,
    github_client: Github,
    max_files: int = 20,
) -> list[Chunk]:
    """
    Ingest markdown files from a single GitHub repo.

    Args:
        repo_name: "owner/repo" format
        github_client: authenticated or anonymous Github client
        max_files: limit files per repo to avoid rate limits
    """
    all_chunks = []

    try:
        repo = github_client.get_repo(repo_name)
        md_files = _find_markdown_files(repo, max_files)

        for file_info in md_files:
            try:
                content = file_info.decoded_content.decode("utf-8", errors="ignore")
                if len(content.strip()) < 100:
                    continue  # skip tiny files

                chunks = chunk_text(
                    text=content,
                    source_type="github",
                    source_name=f"{repo_name}/{file_info.path}",
                    source_url=file_info.html_url,
                    author=repo.owner.login,
                    date=str(repo.pushed_at.date()) if repo.pushed_at else "",
                )
                all_chunks.extend(chunks)

            except Exception as e:
                print(f"    [github] skip {file_info.path}: {e}")

        print(f"  [github] {repo_name} → {len(all_chunks)} chunks from {len(md_files)} files")

    except GithubException as e:
        print(f"  [github] ERROR on {repo_name}: {e.status} {e.data}")

    return all_chunks


def ingest_github_repos(
    repo_names: list[str] = None,
    max_files_per_repo: int = 15,
) -> list[Chunk]:
    """
    Ingest a list of GitHub repos.
    Uses token if available, anonymous otherwise.
    """
    repos = repo_names or DEFAULT_REPOS
    g = Github(GITHUB_TOKEN) if GITHUB_TOKEN else Github()

    all_chunks = []
    for repo_name in repos:
        chunks = ingest_github_repo(repo_name, g, max_files=max_files_per_repo)
        all_chunks.extend(chunks)

    print(f"  [github] total: {len(repos)} repos, {len(all_chunks)} chunks")
    return all_chunks


def _find_markdown_files(repo, max_files: int) -> list:
    """
    Recursively find .md files in a repo.
    Searches root and /docs folder. Stops at max_files.
    """
    md_files = []

    # Always get the README first
    try:
        readme = repo.get_readme()
        md_files.append(readme)
    except Exception:
        pass

    # Search docs/ folder if it exists
    for folder in ["docs", "documentation", "wiki"]:
        try:
            contents = repo.get_contents(folder)
            for item in contents:
                if item.name.endswith(".md") and len(md_files) < max_files:
                    md_files.append(item)
        except Exception:
            pass

    return md_files[:max_files]
