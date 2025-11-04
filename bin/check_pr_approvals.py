#!/usr/bin/env python3
import os
import sys
import requests

def get_reviews(owner, repo, pr_number, token):
    """Fetch all reviews for a given PR."""
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    reviews = []
    page = 1

    while True:
        resp = requests.get(url, headers=headers, params={"per_page": 100, "page": page})
        if resp.status_code != 200:
            print(f"❌ Failed to fetch reviews: {resp.status_code} {resp.text}")
            sys.exit(1)
        data = resp.json()
        if not data:
            break
        reviews.extend(data)
        page += 1

    return reviews


def get_team_members(owner, team_slug, token):
    """Fetch members of a GitHub team."""
    url = f"https://api.github.com/orgs/{owner}/teams/{team_slug}/members"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"}
    members = []
    page = 1

    while True:
        resp = requests.get(url, headers=headers, params={"per_page": 100, "page": page})
        if resp.status_code == 404:
            print(f"⚠️ Team {team_slug} not found or token lacks permission.")
            return []
        elif resp.status_code != 200:
            print(f"❌ Failed to fetch team members for {team_slug}: {resp.status_code} {resp.text}")
            sys.exit(1)

        data = resp.json()
        if not data:
            break
        members.extend([m["login"] for m in data])
        page += 1

    return members


def main():
    # Read required environment variables
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")  # e.g., org/repo
    pr_number = os.getenv("PR_NUMBER")

    if not all([token, repo, pr_number]):
        print("❌ Missing one or more required environment variables: GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER")
        sys.exit(1)

    owner, repo_name = repo.split("/")

    # Fetch PR reviews
    reviews = get_reviews(owner, repo_name, pr_number, token)

    # Get latest review state per user
    latest_reviews = {}
    for r in reviews:
        user = r["user"]["login"]
        latest_reviews[user] = r["state"]

    # Filter approved users
    approved_users = [u for u, s in latest_reviews.items() if s == "APPROVED"]
    print(f"✅ Approved users: {approved_users}")

    if len(approved_users) < 2:
        print("❌ PR must have at least 2 approvals.")
        sys.exit(1)

    # Fetch team members
    datamodelling_team = get_team_members(owner, "datamodelling", token)
    coat_team = get_team_members(owner, "COAT", token)

    # Check team approvals
    has_datamodelling = any(u in datamodelling_team for u in approved_users)
    has_coat = any(u in coat_team for u in approved_users)

    if not has_datamodelling or not has_coat:
        print(f"❌ Missing required team approvals:")
        print(f"  datamodelling approval: {'✅' if has_datamodelling else '❌'}")
        print(f"  COAT approval: {'✅' if has_coat else '❌'}")
        sys.exit(1)

    print("🎉 All approval requirements met!")


if __name__ == "__main__":
    main()
