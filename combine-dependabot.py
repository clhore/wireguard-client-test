#!/usr/bin/env python3
import os
import subprocess
import sys
import json
import requests

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GIT_USERNAME = os.environ.get("GIT_USERNAME", "dependabot[bot]")
GIT_EMAIL = os.environ.get("GIT_EMAIL", "dependabot[bot]@users.noreply.github.com")
BASE_BRANCH = os.environ.get("BASE_BRANCH", "debian/master")
COMBINE_BRANCH = os.environ.get("COMBINE_BRANCH", "combine-dependabot")
BRANCH_PREFIX = os.environ.get("BRANCH_PREFIX", "dependabot")
REPO = os.environ.get("GITHUB_REPOSITORY")
OUTPUT_JSON = os.environ.get("OUTPUT_JSON", "")

def auth_git():
    subprocess.run(["git", "config", "--global", "user.name", GIT_USERNAME], check=True)
    subprocess.run(["git", "config", "--global", "user.email", GIT_EMAIL], check=True)

def run_git(*args, check=True):
    result = subprocess.run(["git"] + list(args), check=check, text=True, capture_output=True)
    return result.stdout.strip()

def branch_exists_remote(branch_name):
    try:
        output = run_git("ls-remote", "--heads", "origin", branch_name)
        return bool(output)
    except subprocess.CalledProcessError:
        return False

def setup_repository():
    print(f"Configurando la rama '{COMBINE_BRANCH}' basada en '{BASE_BRANCH}'...")
    run_git("fetch", "--all")
    if branch_exists_remote(COMBINE_BRANCH):
        print(f"La rama remota '{COMBINE_BRANCH}' ya existe. Realizando checkout.")
        run_git("checkout", COMBINE_BRANCH)
        run_git("reset", "--hard", f"origin/{COMBINE_BRANCH}")
    else:
        run_git("checkout", "-B", COMBINE_BRANCH, BASE_BRANCH)

def get_dependabot_prs():
    print(f"Obteniendo PRs abiertas basadas en '{BASE_BRANCH}' con head que empiece por '{BRANCH_PREFIX}'...")
    owner, repo = REPO.split("/")
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?state=open&base={BASE_BRANCH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    pulls = response.json()

    return [pr for pr in pulls if pr["head"]["ref"].startswith(BRANCH_PREFIX)]

def commit_already_applied(commit_sha):
    try:
        subprocess.run(["git", "merge-base", "--is-ancestor", commit_sha, "HEAD"], check=True)
        print(f"El commit {commit_sha} ya está presente en la rama.")
        return True
    except subprocess.CalledProcessError:
        return False

def get_commit_diff(commit_sha):
    diff = run_git("diff", f"{commit_sha}^!", check=False)
    return diff.strip()

def cherry_pick_pr(pr):
    commit_sha = pr["head"]["sha"]
    pr_number = pr["number"]

    print(f"Realizando cherry-pick del commit {commit_sha} de la PR #{pr_number}...")
    try:
        subprocess.run([
            "git", "cherry-pick", "--strategy=recursive", "-X", "theirs",
            "--empty=drop", commit_sha
        ], check=True)
        print(f"Cherry-pick completado para el commit {commit_sha}")
        return True
    except subprocess.CalledProcessError:
        print(f"Conflicto detectado para la PR #{pr_number}, omitiendo commit...")
        subprocess.run(["git", "cherry-pick", "--skip"], check=False)
        return False

def has_changes():
    status = run_git("status", "--porcelain")
    try:
        ahead = run_git("rev-list", "--count", "--left-only", "@{u}...HEAD")
    except subprocess.CalledProcessError:
        ahead = "0"
    return bool(status.strip()) or int(ahead) > 0

def push_branch():
    #if not has_changes():
    #    print("No hay cambios para empujar. Se omite el push.")
    #    return False
    print(f"Empujando la rama '{COMBINE_BRANCH}' a origin...")
    run_git("push", "-u", "origin", COMBINE_BRANCH), "--force"
    return True

def create_pull_request(pr_list_text):
    #if not pr_list_text:z
    #    print("No se encontraron PRs para combinar, no se creará ninguna nueva PR.")
    #    return
    owner, repo = REPO.split("/")
    title = "Combinar Dependabot: actualizaciones consolidadas"
    body = f"Esta pull request fue creada automáticamente combinando las siguientes PRs de Dependabot:\n\n{pr_list_text}"
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "title": title,
        "head": COMBINE_BRANCH,
        "base": BASE_BRANCH,
        "body": body
    }
    response = requests.post(url, headers=headers, data=json.dumps(data))
    response.raise_for_status()
    pr = response.json()
    print("Pull Request creada:", pr.get("html_url"))

def main():
    auth_git()
    setup_repository()

    prs = get_dependabot_prs()
    if not prs:
        print("No se encontraron PRs de Dependabot para combinar.")
        return

    pr_list_text = ""
    combined_prs = []
    failed_prs = []
    omitted_prs = []

    for pr in prs:
        print(f"Procesando PR #{pr['number']} - {pr['title']}")

        if commit_already_applied(pr["head"]["sha"]) or not get_commit_diff(pr["head"]["sha"]):
            print(f"PR #{pr['number']} ya ha sido aplicada o no tiene cambios efectivos. Omitiendo.")
            omitted_prs.append({
                "number": pr["number"], "title": pr["title"], "url": pr["html_url"]});
            continue
        
        if cherry_pick_pr(pr):
            combined_prs.append({
                "number": pr["number"], "title": pr["title"], "url": pr["html_url"]})
            pr_list_text += f"- #{pr['number']} {pr['title']} ({pr['html_url']})\n"
            continue

        failed_prs.append({
            "number": pr["number"], "title": pr["title"], "url": pr["html_url"]})

    if push_branch():
        create_pull_request(pr_list_text)
    else:
        print("No se realizaron cambios reales. No se creó una nueva PR.")

    if OUTPUT_JSON:
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump({
                "combined_prs": combined_prs,
                "failed_prs": failed_prs,
                "omitted_prs": omitted_prs,
                "branch": COMBINE_BRANCH,
                "base": BASE_BRANCH
            }, f, indent=2)
        print(f"Resultado guardado en {OUTPUT_JSON}")

if __name__ == "__main__":
    if not GITHUB_TOKEN or not REPO:
        print("Error: Asegúrate de que GITHUB_TOKEN y GITHUB_REPOSITORY estén definidos.")
        sys.exit(1)

    try:
        main()
    except Exception as e:
        print("Error durante la combinación de PRs:", str(e))
        sys.exit(1)
