import os
import sys
import fnmatch
from github import Github
from github.GithubException import GithubException


def get_reviews(pull):
    try:
        return list(pull.get_reviews())
    except GithubException as e:
        print(f"❌ Failed to fetch reviews: {e.data}")
        sys.exit(1)


def get_team_members(org, team_slug):
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


def load_codeowners(repo):
    try:
        file = repo.get_contents(".github/CODEOWNERS")
        content = file.decoded_content.decode()
    except Exception:
        print("❌ Unable to read CODEOWNERS file")
        sys.exit(1)

    rules = []
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        pattern = parts[0]
        owners = parts[1:]
        rules.append((pattern, owners))

    return rules


def match_codeowners_for_file(filepath, rules):
    matched_owners = []
    for pattern, owners in rules:
        if fnmatch.fnmatch(filepath, pattern) or fnmatch.fnmatch("/" + filepath, pattern):
            matched_owners = owners
    return matched_owners


def get_required_teams_from_changes(repo, pull):
    rules = load_codeowners(repo)
    changed_files = [f.filename for f in pull.get_files()]
    required_teams = set()

    for fpath in changed_files:
        owners = match_codeowners_for_file(fpath, rules)
        for owner in owners:
            if not owner.startswith("@"):
                continue

            owner = owner[1:]  # remove @

            if "/" in owner:
                org, team_slug = owner.split("/", 1)
                required_teams.add(team_slug)

    return required_teams


def main():
    token = os.getenv("GITHUB_TOKEN")
    repo_name = os.getenv("GITHUB_REPOSITORY")
    pr_number = os.getenv("PR_NUMBER")

    if not all([token, repo_name, pr_number]):
        print("❌ Missing required env vars: GITHUB_TOKEN, GITHUB_REPOSITORY, PR_NUMBER")
        sys.exit(1)

    github_client = Github(token)

    try:
        repo = github_client.get_repo(repo_name)
    except GithubException as e:
        print(f"❌ Failed to access repository {repo_name}: {e.data}")
        sys.exit(1)

    try:
        pull = repo.get_pull(int(pr_number))
    except GithubException as e:
        print(f"❌ Failed to fetch PR #{pr_number}: {e.data}")
        sys.exit(1)

    owner = repo.full_name.split("/")[0]
    org = github_client.get_organization(owner)

    reviews = get_reviews(pull)

    latest_reviews = {}
    for review in reviews:
        latest_reviews[review.user.login] = review.state

    approved_users = [user for user, state in latest_reviews.items() if state == "APPROVED"]
    print(f"✅ Approved users: {approved_users}")

    if len(approved_users) < 1:
        print("❌ PR must have at least 2 approvals.")
        sys.exit(1)

    required_teams = get_required_teams_from_changes(repo, pull)

    if not required_teams:
        print("✅ No team-specific approvals required.")
        print("🎉 All approval requirements met!")
        return

    print(f"📌 Required teams: {list(required_teams)}")

    for team_slug in required_teams:
        team_members = get_team_members(org, team_slug)
        has_team_approval = any(user in team_members for user in approved_users)

        if not has_team_approval:
            print(f"❌ Missing approval from team: {team_slug}")
            sys.exit(1)

    print("🎉 All approval requirements met!")


if __name__ == "__main__":
    main()
