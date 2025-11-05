import os
import sys
from github import Github
from github.GithubException import GithubException

def get_reviews(pull):
    """Fetch all reviews for a given pull request using PyGithub."""
    try:
        return list(pull.get_reviews())
    except GithubException as e:
        print(f"❌ Failed to fetch reviews: {e.data}")
        sys.exit(1)


def get_team_members(org, team_slug):
    """Fetch members of a GitHub team using PyGithub."""
    try:
        team = org.get_team_by_slug(team_slug)
    except GithubException as e:
        if e.status == 404:
            print(f"⚠️ Team {team_slug} not found or token lacks permission.")
            return []
        print(f"❌ Failed to access team {team_slug}: {e.data}")
        sys.exit(1)

    try:
        return [member.login for member in team.get_members()]
    except GithubException as e:
        print(f"❌ Failed to fetch members for team {team_slug}: {e.data}")
        sys.exit(1)


def main():
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")

    if not all([token, repo, pr_number]):
        print("❌ Missing required env vars: GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER")
        sys.exit(1)

    github_client = Github(token)

    try:
        repo = github_client.get_repo(repo)
    except GithubException as e:
        print(f"❌ Failed to access repository {repo}: {e.data}")
        sys.exit(1)

    try:
        pull = repo.get_pull(int(pr_number))
    except GithubException as e:
        print(f"❌ Failed to fetch PR #{pr_number}: {e.data}")
        sys.exit(1)

    owner = repo.full_name.split("/")[0]
    org = github_client.get_organization(owner)

    reviews = get_reviews(pull)

    print(reviews)

    print(reviews[0].state)

    latest_reviews = {}
    for review in reviews:
        latest_reviews[review.user.login] = review.state

    approved_users = [user for user, state in latest_reviews.items() if state == "APPROVED"]
    print(f"✅ Approved users: {approved_users}")

    if len(approved_users) < 2:
        print("❌ PR must have at least 2 approvals.")
        sys.exit(1)

    # datamodelling_team = get_team_members(org, "data-modelling")
    # coat_team = get_team_members(org, "cloud-optimisation-and-accountability")
    datamodelling_team = get_team_members(org, "operations-engineering")
    coat_team = get_team_members(org, "cloud-optimisation-and-accountability")

    has_datamodelling = any(user in datamodelling_team for user in approved_users)
    has_coat = any(user in coat_team for user in approved_users)

    if not has_datamodelling or not has_coat:
        print("❌ Missing required team approvals:")
        print(f"  datamodelling approval: {'✅' if has_datamodelling else '❌'}")
        print(f"  COAT approval: {'✅' if has_coat else '❌'}")
        sys.exit(1)

    print("🎉 All approval requirements met!")


if __name__ == "__main__":
    main()
