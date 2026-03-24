"""
GitHub API client — repos, issues, pull requests, files, code search.
Auth via GITHUB_TOKEN in config/.env (Personal Access Token).
"""
from __future__ import annotations

import base64
import logging
import os

log = logging.getLogger(__name__)


class GitHubError(Exception):
    pass


class GitHubNotConfiguredError(GitHubError):
    pass


def _get_client():
    """Return an authenticated github.Github instance."""
    try:
        from github import Github, GithubException  # noqa: F401
    except ImportError:
        raise GitHubError("PyGithub not installed. Run: pip install PyGithub")

    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise GitHubNotConfiguredError(
            "GITHUB_TOKEN not set. Add it to config/.env and run /auth_github."
        )
    return Github(token)


class GitHubTool:
    """GitHub operations: repos, issues, PRs, files, code search."""

    # ── Auth / identity ───────────────────────────────────────────────────────

    def get_authenticated_user(self) -> dict:
        """Return info about the authenticated GitHub user."""
        gh = _get_client()
        u = gh.get_user()
        return {
            "login": u.login,
            "name": u.name,
            "email": u.email,
            "public_repos": u.public_repos,
            "followers": u.followers,
            "url": u.html_url,
        }

    # ── Repositories ──────────────────────────────────────────────────────────

    def list_repos(self, owner: str | None = None, max_results: int = 30) -> list[dict]:
        """
        List repos for the authenticated user or a given owner/org.
        Returns list of {name, full_name, private, description, url, stars, updated_at}.
        """
        gh = _get_client()
        if owner:
            user_or_org = gh.get_user(owner)
            repos = user_or_org.get_repos()
        else:
            repos = gh.get_user().get_repos()

        results = []
        for r in repos:
            results.append({
                "name": r.name,
                "full_name": r.full_name,
                "private": r.private,
                "description": r.description or "",
                "url": r.html_url,
                "stars": r.stargazers_count,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
            })
            if len(results) >= max_results:
                break
        return results

    def get_repo(self, repo: str) -> dict:
        """
        Get repo details. repo = 'owner/name' or just 'name' (uses auth user as owner).
        Returns {name, full_name, description, private, url, stars, forks, default_branch, topics}.
        """
        gh = _get_client()
        if "/" not in repo:
            repo = f"{gh.get_user().login}/{repo}"
        r = gh.get_repo(repo)
        return {
            "name": r.name,
            "full_name": r.full_name,
            "description": r.description or "",
            "private": r.private,
            "url": r.html_url,
            "clone_url": r.clone_url,
            "stars": r.stargazers_count,
            "forks": r.forks_count,
            "default_branch": r.default_branch,
            "topics": r.get_topics(),
            "open_issues": r.open_issues_count,
        }

    def create_repo(
        self,
        name: str,
        description: str = "",
        private: bool = False,
        auto_init: bool = True,
    ) -> dict:
        """
        Create a new repository under the authenticated user.
        Returns {name, full_name, url, clone_url}.
        """
        gh = _get_client()
        user = gh.get_user()
        r = user.create_repo(
            name=name,
            description=description,
            private=private,
            auto_init=auto_init,
        )
        return {
            "name": r.name,
            "full_name": r.full_name,
            "url": r.html_url,
            "clone_url": r.clone_url,
        }

    # ── Issues ────────────────────────────────────────────────────────────────

    def list_issues(
        self,
        repo: str,
        state: str = "open",
        max_results: int = 20,
    ) -> list[dict]:
        """
        List issues for a repo. repo = 'owner/name' or 'name'.
        state: 'open' | 'closed' | 'all'.
        Returns list of {number, title, state, url, labels, created_at, body_preview}.
        """
        gh = _get_client()
        if "/" not in repo:
            repo = f"{gh.get_user().login}/{repo}"
        r = gh.get_repo(repo)
        issues = r.get_issues(state=state)
        results = []
        for i in issues:
            if i.pull_request:
                continue  # skip PRs that appear in issues list
            results.append({
                "number": i.number,
                "title": i.title,
                "state": i.state,
                "url": i.html_url,
                "labels": [l.name for l in i.labels],
                "created_at": i.created_at.isoformat(),
                "body_preview": (i.body or "")[:200],
            })
            if len(results) >= max_results:
                break
        return results

    def get_issue(self, repo: str, number: int) -> dict:
        """Get a single issue by number. Returns full issue details."""
        gh = _get_client()
        if "/" not in repo:
            repo = f"{gh.get_user().login}/{repo}"
        r = gh.get_repo(repo)
        i = r.get_issue(number)
        return {
            "number": i.number,
            "title": i.title,
            "state": i.state,
            "url": i.html_url,
            "labels": [l.name for l in i.labels],
            "created_at": i.created_at.isoformat(),
            "updated_at": i.updated_at.isoformat(),
            "body": i.body or "",
            "comments": i.comments,
        }

    def create_issue(
        self,
        repo: str,
        title: str,
        body: str = "",
        labels: list[str] | None = None,
    ) -> dict:
        """
        Create a new issue. repo = 'owner/name' or 'name'.
        Returns {number, title, url}.
        """
        gh = _get_client()
        if "/" not in repo:
            repo = f"{gh.get_user().login}/{repo}"
        r = gh.get_repo(repo)
        kwargs: dict = {"title": title, "body": body}
        if labels:
            kwargs["labels"] = labels
        i = r.create_issue(**kwargs)
        return {"number": i.number, "title": i.title, "url": i.html_url}

    def close_issue(self, repo: str, number: int) -> dict:
        """Close an issue. Returns {number, state}."""
        gh = _get_client()
        if "/" not in repo:
            repo = f"{gh.get_user().login}/{repo}"
        r = gh.get_repo(repo)
        i = r.get_issue(number)
        i.edit(state="closed")
        return {"number": i.number, "state": "closed"}

    def comment_on_issue(self, repo: str, number: int, body: str) -> dict:
        """Add a comment to an issue or PR. Returns {id, url}."""
        gh = _get_client()
        if "/" not in repo:
            repo = f"{gh.get_user().login}/{repo}"
        r = gh.get_repo(repo)
        i = r.get_issue(number)
        c = i.create_comment(body)
        return {"id": c.id, "url": c.html_url}

    # ── Pull Requests ─────────────────────────────────────────────────────────

    def list_prs(
        self,
        repo: str,
        state: str = "open",
        max_results: int = 20,
    ) -> list[dict]:
        """
        List pull requests for a repo.
        state: 'open' | 'closed' | 'all'.
        Returns list of {number, title, state, url, head, base, created_at}.
        """
        gh = _get_client()
        if "/" not in repo:
            repo = f"{gh.get_user().login}/{repo}"
        r = gh.get_repo(repo)
        prs = r.get_pulls(state=state)
        results = []
        for p in prs:
            results.append({
                "number": p.number,
                "title": p.title,
                "state": p.state,
                "url": p.html_url,
                "head": p.head.ref,
                "base": p.base.ref,
                "created_at": p.created_at.isoformat(),
                "body_preview": (p.body or "")[:200],
            })
            if len(results) >= max_results:
                break
        return results

    def get_pr(self, repo: str, number: int) -> dict:
        """Get a single pull request by number."""
        gh = _get_client()
        if "/" not in repo:
            repo = f"{gh.get_user().login}/{repo}"
        r = gh.get_repo(repo)
        p = r.get_pull(number)
        return {
            "number": p.number,
            "title": p.title,
            "state": p.state,
            "url": p.html_url,
            "head": p.head.ref,
            "base": p.base.ref,
            "merged": p.merged,
            "mergeable": p.mergeable,
            "created_at": p.created_at.isoformat(),
            "body": p.body or "",
            "changed_files": p.changed_files,
            "additions": p.additions,
            "deletions": p.deletions,
        }

    def create_pr(
        self,
        repo: str,
        title: str,
        head: str,
        base: str = "main",
        body: str = "",
        draft: bool = False,
    ) -> dict:
        """
        Create a pull request. head = branch with changes, base = target branch.
        Returns {number, title, url}.
        """
        gh = _get_client()
        if "/" not in repo:
            repo = f"{gh.get_user().login}/{repo}"
        r = gh.get_repo(repo)
        p = r.create_pull(title=title, body=body, head=head, base=base, draft=draft)
        return {"number": p.number, "title": p.title, "url": p.html_url}

    # ── Files ─────────────────────────────────────────────────────────────────

    def get_file(self, repo: str, path: str, ref: str | None = None) -> dict:
        """
        Get a file's content from a repo.
        Returns {path, content (decoded text), sha, url, encoding}.
        """
        gh = _get_client()
        if "/" not in repo:
            repo = f"{gh.get_user().login}/{repo}"
        r = gh.get_repo(repo)
        kwargs = {}
        if ref:
            kwargs["ref"] = ref
        f = r.get_contents(path, **kwargs)
        if isinstance(f, list):
            # It's a directory — return listing
            return {
                "path": path,
                "type": "directory",
                "contents": [{"name": item.name, "type": item.type, "path": item.path} for item in f],
            }
        content = base64.b64decode(f.content).decode("utf-8", errors="replace")
        return {
            "path": f.path,
            "content": content,
            "sha": f.sha,
            "url": f.html_url,
            "size": f.size,
        }

    def create_or_update_file(
        self,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str | None = None,
    ) -> dict:
        """
        Create or update a file in a repo.
        content should be the plain text (will be encoded to bytes automatically).
        Returns {path, commit_sha, url}.
        """
        gh = _get_client()
        if "/" not in repo:
            repo = f"{gh.get_user().login}/{repo}"
        r = gh.get_repo(repo)
        content_bytes = content.encode("utf-8")
        kwargs: dict = {"message": message, "content": content_bytes}
        if branch:
            kwargs["branch"] = branch

        # Check if file already exists (need sha for update)
        try:
            existing = r.get_contents(path, ref=branch or r.default_branch)
            if not isinstance(existing, list):
                kwargs["sha"] = existing.sha
        except Exception:
            pass  # file doesn't exist yet — create

        result = r.create_file(path, **kwargs) if "sha" not in kwargs else r.update_file(path, **kwargs)
        return {
            "path": path,
            "commit_sha": result["commit"].sha,
            "url": result["content"].html_url,
        }

    def delete_file(
        self,
        repo: str,
        path: str,
        message: str,
        branch: str | None = None,
    ) -> dict:
        """Delete a file from a repo. Returns {path, commit_sha}."""
        gh = _get_client()
        if "/" not in repo:
            repo = f"{gh.get_user().login}/{repo}"
        r = gh.get_repo(repo)
        kwargs: dict = {}
        if branch:
            kwargs["ref"] = branch
        f = r.get_contents(path, **kwargs)
        if isinstance(f, list):
            raise GitHubError(f"{path} is a directory, not a file")
        del_kwargs: dict = {"message": message, "sha": f.sha}
        if branch:
            del_kwargs["branch"] = branch
        result = r.delete_file(path, **del_kwargs)
        return {"path": path, "commit_sha": result["commit"].sha}

    # ── Code search ───────────────────────────────────────────────────────────

    def search_code(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Search code across GitHub.
        query supports qualifiers: repo:owner/name, language:python, etc.
        Returns list of {name, path, repo, url, score}.
        """
        gh = _get_client()
        results_iter = gh.search_code(query)
        results = []
        for item in results_iter:
            results.append({
                "name": item.name,
                "path": item.path,
                "repo": item.repository.full_name,
                "url": item.html_url,
                "score": item.score,
            })
            if len(results) >= max_results:
                break
        return results

    def search_repos(self, query: str, max_results: int = 10) -> list[dict]:
        """
        Search repositories on GitHub.
        Returns list of {name, full_name, description, url, stars}.
        """
        gh = _get_client()
        results_iter = gh.search_repositories(query)
        results = []
        for r in results_iter:
            results.append({
                "name": r.name,
                "full_name": r.full_name,
                "description": r.description or "",
                "url": r.html_url,
                "stars": r.stargazers_count,
                "language": r.language or "",
            })
            if len(results) >= max_results:
                break
        return results
