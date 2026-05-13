---
name: cloudsmith-migration
description: >
  Migrate a project to use Cloudsmith as the primary artifact repository for Python, Node, Docker,
  CI workflows, and Dependabot. This is a multi-step process that involves updating configuration files,
  regenerating lockfiles, updating CI workflows, repository properties, etc.
---

# Migrate a Project to Cloudsmith

## Goal

Migrate an existing project to use **Cloudsmith** as the primary artifact repository, instead of AWS CodeArtifact or
GitHub Packages. The action supports migration of:

- **Python**
- **Node**
- **Docker**
- **GitHub Actions workflows**
- **Dependabot**

The migration is performed in **ordered steps**, with **validation and a separate commit after each step**.

## Cloudsmith Endpoints

Use these endpoints unless the project has a strong reason to differ:

- **Python index**
    - Index URL: `https://dl.artifacts.oura.cloud/basic/main/python/simple/`
    - Publish URL: `https://python.cloudsmith.io/oura/main/`
- **NPM registry**
    - Global registry: `https://npm.artifacts.oura.cloud/main/` (same to publish)
- **Docker registry**
    - Registry: `docker.artifacts.oura.cloud`

## General Workflow

Across all steps:

1. Work gradually:
    - Scan for relevant config files and CodeArtifact/old-registry references
    - Apply edits in small, reviewable chunks
2. **After each numbered step below**:
    - Run the project’s usual **validation** (tests, builds, lints, sample commands)
    - Fix issues caused by the changes
    - Create a **separate commit** per step, e.g.:
        - `chore: Migrate Python to Cloudsmith`
        - `chore: Migrate Node to Cloudsmith`
        - `chore: Migrate Docker to Cloudsmith`
        - `chore: Update CI for Cloudsmith`
        - `chore: Update Dependabot for Cloudsmith`
        - `doc: Update docs for Cloudsmith`
3. When all steps pass:
    - Print out summary of execution
    - Help the user create a PR and fix any remaining issues

## Committing rules

When creating Git commits, obey the repository's usual conventions.

However, when writing a commit message body, do NOT summarize the technical changes:

```markdown
- Update base Dockerfile and docker-compose to pull from docker.artifacts.oura.cloud
- Update local K8s manifests (cdk8s/local)
- EKS production workloads remain on ECR (not yet integrated with Cloudsmith)
```

Also do NOT summarize them like this:

```markdown
Update base Dockerfile and docker-compose to pull from docker.artifacts.oura.cloud
instead of public ECR and Docker Hub. Update local K8s manifests (cdk8s/local)
similarly. EKS production workloads remain on ECR (not yet integrated with Cloudsmith).
```

In general, do NOT summarize the technical changes - those can be seen and read by looking at the diff.

Rather DO:

- Explain briefly the generic business case, ie. why we do this
- Explain any oddities (hacks, weird things, variations from common conventions) that exist or had to be taken
- Explain any potential improvements that there might be room for
- Avoid any marketing terminology, hype, or buzzwords

And yet only include these details, if you're SURE that they are relevant and provide benefit to the user.

Be brief.

## Prerequisites

Before running the steps

1. Ensure the user is not on the `main` / `master` branch. If they are, ask the user to switch to a new branch first.
   Do NOT let the workflow proceed until the user has actually switched to a non-main branch!

2. Investigate the repository and determine which of the following package managers it uses:

    - pip
    - uv
    - Poetry
    - npm
    - Yarn 1.x
    - Yarn 2+
    - Docker

3. Ask confirmation from the user if they have the required Cloudsmith configs in place for the detected package
   managers. Point the user to
   [Cloudsmith docs](https://ouraring.atlassian.net/wiki/spaces/SW/pages/6316621913/Cloudsmith)
   for instructions. Explain to the user that they need (at least) the following configurations in place, for each
   package manager that was detected:

    - `~/.config/pip/pip.conf` if the repository uses pip
    - `~/.config/uv/uv.toml` if the repository uses uv, and they also need `UV_INDEX_CLOUDSMITH_USERNAME` and
      `UV_INDEX_CLOUDSMITH_PASSWORD` in their environment variables
    - `~/.config/pypoetry/config.toml` if the repository uses Poetry
    - `~/.npmrc` if the repository uses npm or Yarn 1.x
    - `~/.yarnrc.yml` if the repository uses Yarn 2+
    - `~/.docker/config.json` if the repository uses Docker

Once the user has confirmed they have the necessary configuration files in place, proceed to step 1.

## Step 1 – Update Python Config & Lock Files

### 1.1 Discover Python configuration

Locate:

- `pyproject.toml`, `uv.toml`, `poetry.toml`, `requirements*.txt`, `setup.cfg`, `.pre-commit-config.yaml`, `Dockerfile`,
  etc.
- Lock files: `uv.lock`, `poetry.lock`, `requirements.lock` / `requirements.txt` if using pip-tools.
- Any CI-specific Python index config (e.g. `UV_INDEX_OURA_*`, `POETRY_*` CodeArtifact URLs).

Search for strings like:

- `codeartifact`
- `.amazonaws.com`
- `UV_INDEX_OURA`
- `POETRY_HTTP_BASIC`
- Old PyPI URLs referencing CodeArtifact

### 1.2 Update project-level Python index to Cloudsmith

1. For **uv-based** projects with `pyproject.toml`, change the Python index to Cloudsmith’s main index:

   ```toml
   [[tool.uv.index]]
   name = "cloudsmith"
   url = "https://dl.artifacts.oura.cloud/basic/main/python/simple/"
   publish-url = "https://python.cloudsmith.io/oura/main/"
   default = true
   ```

   This assumes `UV_INDEX_CLOUDSMITH_USERNAME` and `UV_INDEX_CLOUDSMITH_PASSWORD` as credentials. We can expect
   those to be available (set in user's shell init).

   Remove or update any previous `[[tool.uv.index]]` entries that point to CodeArtifact or other legacy registries.

   Remove any `keyring-provider = "subprocess"` entries from `[tool.uv]` section (and remove the whole section if it
   doesn't have any other entries). Keyring packages can be dropped
   also elsewhere in the project, e.g. in `.pre-commit-config.yaml`, if they are not needed for anything else.

   If any packages in `[tool.uv.sources]` explicitly declare an "oura" or "oura_pypi" index, remove the explicit
   index declaration. For example, remove the `index` declarations (and whole rows if nothing else is configured)
   in these example cases:

   ```toml
   [tool.uv.sources]
   oura-ande-client = { index = "oura_pypi" }
   oura-assa-commons = { index = "oura_pypi", version = "2.1.0" }
   ```

   Cloudsmith index is set as the default index so per package declaration is not needed.

2. For **pip/poetry/pip-tools** with `pyproject.toml`:

   Set the Cloudsmith index as primary:

   ```toml
   [[tool.poetry.source]]
   name = "cloudsmith"
   url = "https://dl.artifacts.oura.cloud/basic/main/python/simple/"
   priority = "primary"
   ```

   Remove any explicit mappings to indexes, if found. Also do NOT add pypi as a supplemental index.

3. For `requirements.in` / `requirements.txt` files:

    - Replace any global or per-index URLs that point to CodeArtifact or other registries with the Cloudsmith main index
      URL `https://dl.artifacts.oura.cloud/basic/main/python/simple/`.
    - Ensure any credentials are **not** hard-coded in project files; they should come from environment or CI (Step 4).

### 1.3 Regenerate Python lockfiles

Use the project’s existing toolchain:

- **uv**:
    - `uv lock`
- **Poetry**:
    - `poetry lock --no-update`
- **pip-tools**:
    - `pip-compile` for each relevant `.in` file

Check that all packages resolve via Cloudsmith (no CodeArtifact URLs remain in the lockfile).

### 1.4 Update related locations

Look for `Dockerfile`, `.pre-commit-config.yaml`, scripts, etc and update any Python index related configuration.
For example, Python credentials may be passed from a script to a `Dockerfile` where they are mounted. Update the
credential names and references accordingly in these places.

### 1.5 Validate Python side

Run the project’s usual Python checks, obeying the project's usual conventions for verifying changes.

Fix any resolution issues before committing.

### 1.6 Commit for Step 1

Create a commit containing only the Python-related changes:

- Python config (`pyproject.toml`, `uv.toml`, `poetry.toml`, etc.)
- Python lock files (`uv.lock`, `poetry.lock`, etc.)
- Any Python-only helper scripts that needed adjustment

Example message: `chore: migrate Python deps to Cloudsmith`.

## Step 2 – Update Node Config & Lock Files

### 2.1 Discover Node configuration

Locate:

- `.yarnrc`, `.yarnrc.yml`, `.npmrc`, `package.json`, `package-lock.json`, `yarn.lock`
- Any Node-specific registry overrides in Dockerfiles or CI workflows

Search for:

- `codeartifact`
- `.amazonaws.com`
- Old npm/npmjs/GitHub registry overrides that are being replaced by Cloudsmith

### 2.2 Update NPM registry to Cloudsmith

- If the project uses Yarn 2+, in `.yarnrc.yml` default to Cloudsmith:

  ```yaml
  npmRegistryServer: https://npm.artifacts.oura.cloud/main/
  npmPublishRegistry: https://npm.artifacts.oura.cloud/main/
  ```

  If the `.yarnrc.yml` file has explicit index for `@jouzen` scope, remove that - Cloudsmith is used for all packages.

- If the project uses Yarn 1.x, in `.yarnrc` define the Cloudsmith index as the global index like so:

  ```
  registry "https://npm.artifacts.oura.cloud/main/"
  ```

- If the project uses npm, in `.npmrc` align it with Cloudsmith:

  ```
  registry=https://npm.artifacts.oura.cloud/main/
  ```

Don't embed any credentials in repository level `.npmrc`, `.yarnrc` or `.yarnrc.yml` files!

### 2.3 Update the Yarn lockfile

- In Yarn 1.x projects, replace all URLs in `yarn.lock` like so:

  ```diff
  -  resolved "https://registry.yarnpkg.com/@ampproject/remapping/-/remapping-2.3.0.tgz#ed441b6fa600072520ce18b43d2c8cc8caecc7f4"
  +  resolved "https://npm.artifacts.oura.cloud/main/@ampproject/remapping/-/remapping-2.3.0.tgz#ed441b6fa600072520ce18b43d2c8cc8caecc7f4"
  ```

  Specifically, for `@jouzen` scoped packages the URL changes so that:

  ```diff
  -  resolved "https://npm.pkg.github.com/download/@jouzen/oura-cdk/2.63.1/54e2a05684cb0a62f42bf78bb13dfce36482c81f#54e2a05684cb0a62f42bf78bb13dfce36482c81f"
  +  resolved "https://npm.artifacts.oura.cloud/main/@jouzen/oura-cdk/-/oura-cdk-2.63.1.tgz#54e2a05684cb0a62f42bf78bb13dfce36482c81f"
  ```

- In Yarn 2+ projects, if the existing `yarn.lock` file has `::__archiveUrl` entries, remove those patterns
  and let Yarn re-resolve:

    - Look for entries like:

      ```
      resolution: "@jouzen/ecom-utils@npm:1.0.2::__archiveUrl=..."
      ```

    - Rewrite to:

      ```
      resolution: "@jouzen/ecom-utils@npm:1.0.2"
      ```

- In npm projects, manually replace the `resolved` fields in the `package-lock.json` so that:

  ```diff
  -      "resolved": "https://registry.npmjs.org/@ampproject/remapping/-/remapping-2.3.0.tgz",
  +      "resolved": "https://npm.artifacts.oura.cloud/main/@ampproject/remapping/-/remapping-2.3.0.tgz",
  ```

  Do the same all URLs that are not `npm.artifacts.oura.cloud` (we now use Cloudsmith for all packages).

### 2.4 Regenerate the lockfile

Run the appropriate command to refresh the lockfile against Cloudsmith:

- Yarn 2+: `yarn install --refresh-lockfile`
- Yarn 1.x: `yarn install --update-checksums`
- npm: `npm install`

Ensure the lock files no longer reference CodeArtifact or other legacy registries for the packages that should
live in Cloudsmith.

### 2.5 Update related locations

Find if there are any NPM index related configuration in `Dockerfile`, `.pre-commit-config.yaml` and scripts.
For example, credentials may be passed to a `Dockerfile` from a script that triggers it. Update the
credential names and references accordingly in these places.

### 2.6 Validate Node side

Run the project’s usual JS/TS checks, obeying the project's usual conventions for verifying changes.

Fix any resolution/build issues before committing.

### 2.7 Commit for Step 2

Create a commit containing only the JS/TS/Yarn/NPM-related changes:

- `.yarnrc.yml` / `.yarnrc` / `.npmrc`
- `package.json`, `package-lock.json`
- `yarn.lock`

Example message: `chore: migrate Node deps to Cloudsmith`.

## Step 3 – Update Docker & docker-compose

### 3.1 Discover Docker-related usage

Locate:

- `Dockerfile`, `Dockerfile.*`, `docker-compose.yml` / `.yaml`
- Any scripts or Make/mise tasks that run `docker build`, `docker tag`, `docker push`, `docker pull` commands
- Kubernetes manifests (usually import `cdk8s` Node packages)

Search within those for:

- `codeartifact`
- ECR
- `dkr.ecr`
- `.amazonaws.com`
- `docker`
- `image`
- `FROM` (uppercase)
- Any upstream (e.g. Docker Hub) images, because we can now proxy those through Cloudsmith

### 3.2 Update Docker registry usage

If images are pulled or pushed from/to registries that should now live in Cloudsmith, change:

- `FROM` lines or `docker pull`/`docker push` commands to use `docker.artifacts.oura.cloud/main` always
  - IF the image reference is **without explicit host** AND lacks **namespace**, add `library` as namespace.
    For example:

    - `FROM node:24` is converted as `FROM docker.artifacts.oura.cloud/main/library/node:24` (adding the `library/`)
    - `FROM 837204174066.dkr.ecr.eu-central-1.amazonaws.com/some-system:1.23` is converted as
      `FROM docker.artifacts.oura.cloud/main/some-system:1.23` (no `library/` added, due to explicit host)
- Any references to CodeArtifact or legacy private registries for images that now exist in Cloudsmith
- Convert any references without an explicit registry to use `docker.artifacts.oura.cloud/main`
  (e.g. `FROM node:24.13.1-bookworm-slim` to `docker.artifacts.oura.cloud/main/library/node:24.13.1-bookworm-slim`)
- In any scripts that call `docker build`, `docker tag`, `docker push` or `docker pull`, change the registry or tag
  to reference `docker.artifacts.oura.cloud/main` always. If the script used to fetch
  CodeArtifact credentials, drop those as they're not needed any longer (assumption is that caller has their
  `~/.docker/config.json` authenticated to Cloudsmith).
- Do NOT touch the `.github/` files (GitHub Actions workflows) yet - those are updated in Step 4.

### 3.3 Update image references in Kubernetes manifests

In Kubernetes manifests (normally in `infra/` or `cdk/`), update the image reference URL so that:

```diff
-            image: `${envProps.env.account}.dkr.ecr.${envProps.env.region}.amazonaws.com/some-system/some-service:${labels.version}`,
+            image: `docker.artifacts.oura.cloud/main/some-system/some-service:${labels.version}`,
```

### 3.4 AWS Lambda & ECR exception

AWS Lambda **requires** ECR, so if the image is used for AWS Lambda, do not remove the ECR registry.

**Keep pushing to ECR registries for images used in AWS Lambda.** Do this **in addition** to pushing to Cloudsmith.
AWS Lambda images must be pushed to both Cloudsmith and ECR.

### 3.5 Validate Docker side

Run the project’s usual Docker flows (locally or via mise/Make/scripts):

- For example: `mise run build:docker` or equivalent
- Ensure images can be built with Cloudsmith endpoints and without CodeArtifact-specific steps

Fix issues before committing.

### 3.6 Commit for Step 3

Create a commit with Docker-only changes:

- `Dockerfile*`
- `docker-compose.*`
- Kubernetes manifests
- Any helper scripts or mise tasks used only for Docker flows

Example message: `chore: migrate Docker to Cloudsmith`.

## Step 4 – Update CI Workflows

This step focuses on **GitHub Actions** (or equivalent CI) and must:

- Replace CodeArtifact auth with **Cloudsmith OIDC**
- Ensure all package and image operations use Cloudsmith tokens
- Remove obsolete CodeArtifact-specific workflows and secrets
- Pass any necessary variables and/or secrets explicitly to **composite actions** as they cannot directly
  access them (e.g. `vars.CLOUDSMITH_PULL_USERNAME`)

### 4.1 Discover workflows to update

Identify workflows that:

- Install Python or Node dependencies in CI
- Build or push Docker images

Common paths:

- `.github/workflows/*.yml` / `.yaml`
- Reusable actions under `.github/actions/`

Search for:

- `codeartifact`
- `aws-actions/configure-aws-credentials`
- `get-authorization-token`
- `UV_INDEX_OURA_*`, `POETRY_*`
- `Hard-coded tokens or legacy raw URLs`

### 4.2 Add Cloudsmith OIDC login

For each workflow that needs Cloudsmith access:

1. Ensure the workflow (or job) has the required permissions:

   ```yaml
   permissions:
     id-token: write   # needed for Cloudsmith OIDC
     contents: read    # Typical for actions/checkout
   ```

2. Figure out what the latest 2.x version of `cloudsmith-io/cloudsmith-cli-action` is, and use that in the next step. 

   For example, at the time of writing, the latest version is `159f1619275d5d3147f059c3cc110938ec221d16` (v2.0.3).

3. Add a Cloudsmith OIDC authentication step, using the appropriate service slug:

    - **Pull-only workflows** (e.g., PR checks):

      ```yaml
      - name: Authenticate with Cloudsmith via OIDC
        id: cloudsmith-login
        uses: cloudsmith-io/cloudsmith-cli-action@159f1619275d5d3147f059c3cc110938ec221d16 # v2.0.3
        with:
          oidc-namespace: oura
          oidc-service-slug: ${{ vars.CLOUDSMITH_PULL_USERNAME }}
          oidc-auth-only: true
      ```

    - **Publish workflows** (e.g., releasing packages/images) need different service slug (push, not pull):

      ```yaml
      - name: Authenticate with Cloudsmith via OIDC
        id: cloudsmith-login
        uses: cloudsmith-io/cloudsmith-cli-action@159f1619275d5d3147f059c3cc110938ec221d16 # v2.0.3
        with:
          oidc-namespace: oura
          oidc-service-slug: ${{ vars.CLOUDSMITH_PUSH_USERNAME }}
          oidc-auth-only: true
      ```

   The action exposes a token that can be used as:

    - `CLOUDSMITH_API_KEY` env var
    - Or referenced directly from `steps.cloudsmith-login.outputs.oidc-token`

   Once these changes are made, for each workflow that was modified, do an audit to ensure that `id-token: write` and `contents: read` are sufficient permissions for all the steps in the workflows; by defining a `permissions:` block at the workflow or job level, we might have reduced permissions for some steps, so ensure that all steps still have the permissions they need. If more permissions are needed, add them to the `permissions:` block along with comments explaining why they're needed.

### 4.3 Use Cloudsmith for Python

In Python-related steps:

1. After Cloudsmith login, pass the Cloudsmith index using a step-scoped environment variable:

   For Pip, like:

   ```yaml
   - name: Pip install
     run: pip install -r requirements.txt
     env:
       PIP_INDEX_URL: https://token:${{ steps.cloudsmith-login.outputs.oidc-token }}@dl.artifacts.oura.cloud/basic/main/python/simple/
   ```

   For uv, like:

   ```yaml
   - name: Uv sync
     run: uv sync --locked
     env:
       UV_INDEX_CLOUDSMITH_USERNAME: token
       UV_INDEX_CLOUDSMITH_PASSWORD: ${{ steps.cloudsmith-login.outputs.oidc-token }}
   ```

   For Poetry, like:

   ```yaml
   - name: Poetry install
     run: poetry install
     env:
       POETRY_HTTP_BASIC_CLOUDSMITH_USERNAME: token
       POETRY_HTTP_BASIC_CLOUDSMITH_PASSWORD: ${{ steps.cloudsmith-login.outputs.oidc-token }}
   ```

2. Remove CodeArtifact-related logic, for example:

    - Calls to `aws codeartifact get-authorization-token`.
    - `UV_INDEX_OURA_USERNAME` / `UV_INDEX_OURA_PASSWORD` which hold CodeArtifact credentials

Ensure the environment now only references Cloudsmith.

### 4.4 Use Cloudsmith for Node

First, configure `actions/setup-node` action so that:

1. For npm & Yarn 1.x, point the `registry-url` to Cloudsmith:

   ```yaml
   - name: Setup Node.js
     uses: actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e # v6.4.0
     with:
       registry-url: https://npm.artifacts.oura.cloud/main/
       always-auth: true  # only if on Yarn 1.x
   ```

   Also, on Yarn 1.x add `always-auth: true` as indicated by the comment (don't include the comment).
   
   If Yarn 1.x is used, do NOT use newer than v5.0.0 of `setup-node` action (v6 or newer does not support
   passing `always-auth` anymore). Downgrade, if you must.

2. For Yarn 2+, don't define an explicit `registry-url` - Yarn 2+ doesn't read the generated `.npmrc` so it doesn't
   matter.

Next, configure the installation steps so that:

1. For npm, pass the auth as `NODE_AUTH_TOKEN` (as supported by the CI created `.npmrc` file):

   ```yaml
   - name: Npm install
     run: npm ci
     env:
       NODE_AUTH_TOKEN: ${{ steps.cloudsmith-login.outputs.oidc-token }}
   ```

2. For Yarn 1.x, pass the auth as `NODE_AUTH_TOKEN` (as supported by the CI created `.npmrc` file):

   ```yaml
   - name: Yarn install
     run: yarn install --frozen-lockfile
     env:
       NODE_AUTH_TOKEN: ${{ steps.cloudsmith-login.outputs.oidc-token }}
   ```

3. For Yarn 2+, pass the auth as `YARN_NPM_AUTH_TOKEN`:

   ```yaml
   - name: Yarn install
     run: yarn install --immutable
     env:
       YARN_NPM_AUTH_TOKEN: ${{ steps.cloudsmith-login.outputs.oidc-token }}
       YARN_NPM_ALWAYS_AUTH: true  # this is needed, too
   ```

### 4.5 Use or add Cloudsmith for Docker

**EXCEPTION: Do NOT remove ECR publishing for images which are used in AWS Lambda!** AWS Lambda **needs** ECR,
so if the image is used for AWS Lambda, do not remove the ECR. In those cases, retain the ECR publishing steps
and **add** the Cloudsmith publishing, too.

1. Any workflow that pulls from or pushes to Cloudsmith must acquire Cloudsmith credentials:

   ```yaml
   - name: Login to Docker Cloudsmith
     uses: docker/login-action@4907a6ddec9925e35a0a9e82d7399ccc52663121 # v4.1.0
     with:
       registry: docker.artifacts.oura.cloud
       username: ${{ vars.CLOUDSMITH_PULL_USERNAME }}  # or PUSH, if publishing is needed
       password: ${{ steps.cloudsmith-login.outputs.oidc-token }}
   ```

   Ensure this step runs in any job that:

    - Pulls base images from `docker.artifacts.oura.cloud`
    - Pushes images there

2. Change any base image tags, when passed in:

   ```yaml
     - name: Build base image
       id: docker-build-base
       uses: docker/build-push-action@v6
       with:
         build-args: |
           BASE_IMAGE=${{ steps.login-dev-ecr.outputs.registry }}/some-system/some-service
   ```

   Change as:

   ```yaml
     - name: Build base image
       id: docker-build-base
       uses: docker/build-push-action@v6
       with:
         build-args: |
           BASE_IMAGE=docker.artifacts.oura.cloud/main/some-system/some-service
   ```

   The `BASE_IMAGE` tag might be declared in `Dockerfile`.

3. Add or replace Cloudsmith registry in tags:

   ```yaml
     - name: Build base image
       id: docker-build-base
       uses: docker/build-push-action@v6
       with:
         tags: ${{ steps.login-dev-ecr.outputs.registry }}/some-system/some-service:${{ version }}
   ```

   For images which are for **AWS Lambda**, **add** Cloudsmith index as publish target:

   ```yaml
         tags: |
           ${{ steps.login-dev-ecr.outputs.registry }}/some-system/some-service:${{ version }}
           docker.artifacts.oura.cloud/main/some-system/some-service:${{ version }}
   ```

   For **other than AWS Lambda images**, only replace the tag:

   ```yaml
         tags: docker.artifacts.oura.cloud/main/some-system/some-service:${{ version }}
   ```

### 4.6 Remove CodeArtifact remnants

Delete or refactor:

- Any dedicated workflows that only refreshed CodeArtifact tokens (e.g. cron workflows updating secrets)
- Secrets/variables that are no longer needed (though secret deletion is manual in GitHub UI)
- AWS credential configuration that existed solely for CodeArtifact package downloads
- `packages: read` permissions when GitHub Packages was previously used

**Keep AWS/ECR configuration where still needed** (e.g., Docker and Lambda images requiring ECR).

### 4.7 Commit for Step 4

Create a commit with **only CI/workflow changes**:

Example message: `chore: update CI to use Cloudsmith OIDC`

## Step 5 – Update Dependabot Config

First search for Renovate config (`renovate.json`, `renovate.json5`, etc). Act depending on the outcome:

- If Renovate config is found, SKIP this step
- If Renovate config is not found, proceed to update or add Dependabot config as instructed in this step

### 5.1 Locate Dependabot config

Find:

- `.github/dependabot.yml` or `.github/dependabot.yaml`

Search within for:

- `codeartifact`
- Old registry URLs (CodeArtifact, GitHub-only, etc.)

### 5.2 Configure Cloudsmith registries

Update `registries:` to define Cloudsmith-backed registries for Python, npm, and Docker (but only when the project
uses each), replacing CodeArtifact:

```yaml
registries:
  oura-pypi:
    type: python-index
    url: https://dl.artifacts.oura.cloud/basic/main/python/simple/
    audience: https://github.com/jouzen
    namespace: oura
    service-slug: ${{ secrets.CLOUDSMITH_USERNAME }}
    replaces-base: true

  oura-npm:
    type: npm-registry
    url: https://npm.artifacts.oura.cloud/main/
    audience: https://github.com/jouzen
    namespace: oura
    service-slug: ${{ secrets.CLOUDSMITH_USERNAME }}
    replaces-base: true

  oura-docker:
    type: docker-registry
    url: docker.artifacts.oura.cloud
    audience: https://github.com/jouzen
    namespace: oura
    service-slug: ${{ secrets.CLOUDSMITH_USERNAME }}
    replaces-base: true
```

Remove any **CodeArtifact-specific** registries and tokens.

### 5.3 Attach registries to updates

Under each `updates:` entry, ensure the appropriate registry names are referenced, for example:

```yaml
updates:
  - package-ecosystem: pip
    registries:
      - oura-pypi

  - package-ecosystem: uv
    registries:
      - oura-pypi

  - package-ecosystem: npm
    registries:
      - oura-npm

  - package-ecosystem: docker
    registries:
      - oura-docker

  - package-ecosystem: docker-compose
    registries:
      - oura-docker
```

Alternatively, registries may be pointed to using a wildcard if that's the repository's convention:

```yaml
updates:
  - package-ecosystem: "uv"
    registries: "*"
```

### 5.4 Commit for Step 5

Create a final commit with only Dependabot changes:

Example message: `chore: update Dependabot registries to Cloudsmith`

## Step 6 - Check repository configuration

This step does not generate a diff, don't commit anything for this step.

Repositories **may** need certain configuration, for example, custom properties. Each subtask defines the rules
for determining what needs to be done, and provides instructions for execution.

### 6.1 `cloudsmith-allow-push-from-pr` property

If the repository has **pull request** workflows, which need **push** access to Cloudsmith
(i.e. they use `vars.CLOUDSMITH_PUSH_USERNAME`), the repository needs `cloudsmith-allow-push-from-pr` property
set to `true`:

- If the user has `gh` CLI available, ASK the user if they want to update the property (explain why it's needed)
- If the user does NOT have `gh` CLI, instruct the user to update the property manually (explain why they need it)

## Step 7 - Update documentation

Finally, update any documentation that the project might have, reflecting the changes from CodeArtifact to Cloudsmith,
noting changes in the workflows, configuration, etc.

## Finalization

Once all the steps are completed and individually validated:

1. Ensure there are no remaining references to:

    - CodeArtifact domains
    - Old package indexes/registries for Python/Node/Docker that should now be Cloudsmith

2. Help the user to create a pull request

    - Provide a brief PR title & description so that:
        - Summarize the migration steps
        - Link to the Cloudsmith Confluence documentation
        - Note any intentional exceptions (e.g. still using ECR for Lambda)
        - Changes are grouped by domain (Python/Node/Docker/CI/Dependabot)
        - Each step has been validated independently
    - Ask the user if they want to create a pull request - if they agree, push the changes (first ensure we are on
      a feature branch!) and create a PR.

3. Help user to fix any remaining errors

    - Ask the user to tell when pull request checks have run
    - Use `gh` CLI to look up the pull request, and view the outcome of checks
    - If there are any errors, investigate and iterate to fix them
