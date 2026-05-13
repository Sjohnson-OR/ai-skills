---
name: github-onboarding
description: >
  Use ONLY when the user explicitly asks for help with Git or GitHub — setting up
  access, cloning repos, SSH keys, Git config, or joining the Oura GitHub org.
  Do NOT trigger for general coding, deployment, or vibe coding tasks unless the
  user hits a Git/GitHub blocker and asks for help with it.
---

# Oura GitHub Onboarding

Guide employees and contractors through setting up GitHub "the Oura way": account creation, security, org access, SSH keys, Git configuration, and repo access.

**jouzen** = Oura's GitHub organization (github.com/jouzen). When people say "Oura GitHub", "Oura's org", or "Oura repos", they mean jouzen. All Oura code lives here.

> **Common scenario:** You've been vibe coding with an AI tool and want to deploy your app, share your code, or collaborate with teammates — that requires GitHub access. This guide gets you set up.

> **When in doubt about Oura-specific details** (internal tools, team names, Confluence pages, ServiceNow items): ask **Glean**, Oura's internal knowledge search. It has access to company docs that this guide may not cover.

## How to Guide the User

**Give 1–2 steps at a time, then stop and wait for the user's reply before continuing.**

- Do NOT dump all phases at once — guide like a conversation, not a document
- After each step or pair of steps, ask: "Did that work?" or "Let me know when you're ready for the next step"
- If the user confirms success, continue to the next 1–2 steps
- If they hit a problem, troubleshoot before moving on
- Skip phases the user has already completed based on their answers

## Start Here: Ask These Questions First

Before doing anything, find out:

1. **GitHub status** — Do you already have a GitHub account linked to your @ouraring.com email? How far along are you — no account yet, account set up but not in jouzen, or in jouzen but need repo access?
2. **OS** — macOS, Linux, or Windows? (affects SSH key commands)

Ask these questions first, then **wait for the user's answers** before suggesting any steps. Use their answers to skip phases they've already completed and tailor examples to their OS.

---

## Phase 1: GitHub Account

**Rule:** Oura requires a GitHub account tied to your **@ouraring.com** email. Do not use a personal-only account.

### No GitHub account yet

1. Go to [github.com/signup](https://github.com/signup)
2. Sign up with your **firstname.lastname@ouraring.com** email
3. Set your public profile Name to **"First Last"** (real name required)
4. Optionally set Company = "Ōura"

### Already have a personal GitHub account

**Recommendation: create a fresh Oura-specific account** at [github.com/signup](https://github.com/signup) using your @ouraring.com email. This keeps work and personal activity cleanly separated and avoids issues with SSO, 2FA, and access scoping.

---

## Phase 2: Enable Two-Factor Authentication (2FA)

2FA is **required** for Oura GitHub membership. Do this before requesting org access.

1. GitHub → Settings → Password and authentication
2. Enable two-factor authentication
3. Use an authenticator app: **Google Authenticator** (recommended)
4. Save your recovery codes somewhere safe

---

## Phase 3: Request Access to jouzen (ServiceNow + SSO)

You need two things: a ServiceNow ticket to get approved, and an SSO login step to actually join the org.

### Step 1: Submit a ServiceNow request

1. Open **ServiceNow** → Service Catalog → Search for **"GitHub"**
2. Open the **GitHub Login Access** catalog item
3. Fill in the justification field — include your department, role, and squad:
   > "SWE Productivity, Senior SRE in Cloud Platform — joining jouzen to work on core infrastructure"
4. Submit and wait for approval (usually same-day for employees)

### Step 2: Join jouzen via Google SSO

Once approved:

1. Open the Google Apps launcher (the 9-dot grid in Gmail/Chrome)
2. Find and click **GitHub Business**
3. Log in with your **ouraring.com** Google account
4. This SSO flow adds your GitHub account to the jouzen organization

You only need to do this SSO step once. After joining, you can use regular [github.com](https://github.com) — SSO is re-used silently.

---

## Phase 4: SSH Key Setup

SSH keys let you push and pull code securely without typing your password. **ed25519** is the preferred key type.

### Generate a key pair

**macOS / Linux:**
```bash
ssh-keygen -t ed25519 -C "firstname.lastname@ouraring.com"
# Press Enter to accept the default path (~/.ssh/id_ed25519)
# Enter a strong passphrase (don't leave it empty)
```

**Windows (PowerShell):**
```powershell
ssh-keygen -t ed25519 -C "firstname.lastname@ouraring.com"
# Accept default path, use a strong passphrase
```

### Add key to SSH agent

**macOS / Linux:**
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```

**Windows (PowerShell):**
```powershell
Start-Service ssh-agent
ssh-add $env:USERPROFILE\.ssh\id_ed25519
```

### Add public key to GitHub

1. Copy your public key:
   - macOS: `pbcopy < ~/.ssh/id_ed25519.pub`
   - Linux: `cat ~/.ssh/id_ed25519.pub` (then copy the output)
   - Windows: `Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub | clip`
2. Go to GitHub → Settings → SSH and GPG keys → **New SSH key**
3. Paste and save

### Authorize the key for jouzen (SSO) — critical step

Without this, git operations against `github.com/jouzen/...` will fail even with a valid key.

1. In GitHub → Settings → SSH and GPG keys
2. Find your key, click **Configure SSO** → **Authorize** → select **jouzen**

### Test it

```bash
ssh -T git@github.com
# Expected: "Hi <username>! You've successfully authenticated..."
```

---

## Phase 5: Configure Local Git Identity

Your commits must be linked to your Oura GitHub account. Set this globally:

```bash
git config --global user.name "First Last"
git config --global user.email "firstname.lastname@ouraring.com"
```

Verify:
```bash
git config --global user.name
git config --global user.email
```

If you manage multiple identities (work + personal), you can override per-repo:
```bash
# Inside a specific repo directory:
git config user.email "firstname.lastname@ouraring.com"
```

---

## Phase 6: Verify Access

After joining jouzen, check:

1. Can you visit [github.com/jouzen](https://github.com/jouzen) and see internal repos?
2. Can you clone a repo?

```bash
# Test with a common internal repo (backend example):
git clone git@github.com:jouzen/api.git

# Mobile:
git clone git@github.com:jouzen/ecore.git
```

If you **can't see internal repos at all** → revisit Phase 3 (ServiceNow ticket approved? SSO step done?)

If you **can see repos but can't push** → you need write access via a GitHub team (Phase 7).

---

## Phase 7: Request Write Access to Repos (GitHub Teams)

Read access to internal repos comes with jouzen membership. **Write access** is managed via GitHub teams tied to systems and squads.

### Two patterns for requesting access

**Option A — AWS Permissions (preferred for most engineers):**
1. ServiceNow → Service Catalog → **AWS Permissions**
2. Select the system/service you'll work on
3. Choose your role: **developer** (most people) or **admin** (leads/SREs)
4. This grants AWS access **and** adds you to the matching GitHub team (e.g. `github-{system}-developer`)

**Option B — GitHub System Permissions (some areas still use this):**
1. ServiceNow → Service Catalog → **GitHub System Permissions**
2. Select the specific GitHub team(s) you need (e.g. `github-core-developer`)

### What team do I need?

- Ask your **manager or onboarding buddy** — they know which systems your squad owns
- Check your squad's **Tools & Services** or onboarding page in Confluence for a list of required teams
- Do **not** ask for per-user repo permissions — always go through teams

---

## Troubleshooting

| Problem | What to check |
|---|---|
| Can't see jouzen repos | ServiceNow ticket approved? Completed GitHub SSO login? |
| SSH: `Permission denied (publickey)` | Key added to GitHub? Authorized for jouzen SSO? `ssh-add` run? |
| Commits show wrong author | Run `git config --global user.email` — must match @ouraring.com |
| ServiceNow ticket stuck | Ping your manager or buddy to approve; check ticket status in ServiceNow |
| Not sure which team to request | Ask your manager, squad TL, or search **Glean** for your squad's onboarding docs |
| Something not covered here | Search **Glean** — it indexes Confluence, Notion, and other internal docs |

For unresolved issues: contact **IT via ServiceNow** for account/access issues, or ask in your squad's Slack channel for team-specific questions.

---

## Quick Checklist

- [ ] GitHub account with @ouraring.com email
- [ ] Real name set in GitHub public profile
- [ ] 2FA enabled
- [ ] ServiceNow GitHub Login Access ticket submitted and approved
- [ ] Joined jouzen via GitHub Business SSO
- [ ] SSH key generated, added to GitHub, and authorized for jouzen
- [ ] `git config --global user.name` and `user.email` set
- [ ] Can clone a jouzen repo over SSH
- [ ] Write-access teams requested for your system(s)
