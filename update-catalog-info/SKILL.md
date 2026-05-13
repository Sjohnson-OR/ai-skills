---
name: update-catalog-info
description: Create or update the `catalog-info.yaml` file with Backstage Software Catalog content. Crawl through the repository, parse any catalog units and write the information into the catalog file.
allowed-tools: Read, Grep, Glob, Write(/catalog-info.yaml), AskUserQuestion
---

# Skill: Update catalog-info.yaml

Create or update `catalog-info.yaml` to register a repository in ŌURA's Backstage Software Catalog. The file describes the System, its Components, APIs, and Resources using Backstage entity descriptors.

## Entity templates

Templates for each entity kind are in the `assets/` directory next to this skill file:

- `assets/system.yaml` — System entity template
- `assets/component.yaml` — Component entity template
- `assets/api.yaml` — API entity template
- `assets/resource.yaml` — Resource entity template

Use these templates as the basis for each entity. Fill in every `<placeholder>` with the values discovered in the steps below. Remove placeholders that do not apply (e.g. remove `providesApis` if the component exposes no APIs; remove `backstage.io/kubernetes-*` annotations if not deployed to Kubernetes).

## Prerequisites

### Glean MCP server

Cross-system entity relations **must** be validated against the live Backstage catalog before they are written into `catalog-info.yaml`. This validation requires the `glean_default` MCP server connection.

**Before proceeding**, verify that the Glean MCP server is available in your current session by checking whether `glean_default` is listed among your MCP servers.

If it is **not** available, stop immediately and instruct the user:

> **Action required — Glean MCP not connected.**
> This skill validates Backstage entity references against the live catalog using the Glean MCP server.
> Please connect the Glean MCP server to your AI coding tool before continuing:
>
> **Claude Code**
>
> ```bash
> claude mcp add glean_default -t http -s user https://oura-be.glean.com/mcp/default
> ```
>
> Then restart the `claude` session and run `/mcp` to authenticate.
>
> **Cursor**
>
> Add the following to your MCP configuration file (`~/.cursor/mcp.json`):
>
> ```json
> {
>   "mcpServers": {
>     "glean_default": {
>       "url": "https://oura-be.glean.com/mcp/default"
>     }
>   }
> }
> ```
>
> Then reload Cursor and authenticate when prompted.
>
> **Gemini CLI**
> Add the following to your MCP configuration file (`~/.gemini/settings.json`):
>
> ```bash
> gemini mcp add --transport http glean_default https://oura-be.glean.com/mcp/default
> ```
>
> Then restart the `gemini` session and run `/mcp auth glean_default` to authenticate.

## Validating Entity Refs via Glean MCP

Use this procedure whenever a step requires confirming that an entity exists in the live Backstage catalog before writing a ref into `catalog-info.yaml`.

1. **Search** using the `glean_default` MCP server with a query combining the entity kind and name, e.g.:
   - `"backstage group my-team"` — for a Group
   - `"backstage domain platform"` — for a Domain
   - `"backstage component oura-foo"` — for a Component
   - `"backstage API foo-service-api"` — for an API
   - `"backstage resource foo-db"` — for a Resource

2. **Note the kind, namespace, and name** from the result — use the exact lowercase values returned; do not construct them manually. Do not blindly paste the full `{kind}:{namespace}/{name}` string into the YAML — each relation field has its own required format (see [Defining Relations](#defining-relations)).

3. **If found**: use the validated ref.

4. **If not found**: do not write the ref; handle per the calling step's instructions.

## Defining Relations

Read this before starting the workflow — Steps 3 and 6 rely on these field semantics and ref formats.

Relations are links between entities. They are **directional** and come in symmetric pairs — each side describes the same link from its own perspective. For example, a Component with `spec.providesApis: [my-api]` causes the API entity to automatically carry the reverse relation `apiProvidedBy`. You never write both directions manually; the catalog derives the reverse automatically.

Relations are derived by the catalog from specific `spec.*` fields in the YAML:

| Field on source entity                      | Relation generated (source → target) | Reverse relation (target → source) |
| ------------------------------------------- | ------------------------------------ | ---------------------------------- |
| `spec.owner`                                | `ownedBy`                            | `ownerOf`                          |
| `spec.maintainedBy` (Oura custom extension) | `maintainedBy`                       | `maintainerOf`                     |
| `spec.providesApis`                         | `providesApi`                        | `apiProvidedBy`                    |
| `spec.consumesApis`                         | `consumesApi`                        | `apiConsumedBy`                    |
| `spec.dependsOn`                            | `dependsOn`                          | `dependencyOf`                     |
| `spec.system`                               | `partOf`                             | `hasPart`                          |

**Entity ref formats** used in relation fields:

- `spec.owner` / `spec.maintainedBy` — short form, kind (`Group`) is implied: `<group-name>` (same namespace) or `<group-namespace>/<group-name>` (cross-namespace)
- `spec.providesApis` / `spec.consumesApis` — short form, kind (`API`) is implied: `<api-name>` (same namespace) or `<api-namespace>/<api-name>` (cross-namespace)
- `spec.dependsOn` — full ref required: `component:<namespace>/<name>` or `resource:<namespace>/<name>`
- `spec.system` — short form, kind (`System`) is implied: `<system-name>` (same namespace) or `<system-namespace>/<system-name>` (cross-namespace)

## Workflow

### Step 1: Check for an existing catalog-info.yaml

If `catalog-info.yaml` already exists, read it before making any changes. When updating:

- Preserve all manually curated fields: links, descriptions, custom annotations.
- Add or update fields; do not remove content unless explicitly asked to.

### Step 2: Identify the system

Determine the system name, title, and description by reading:

- The repository name
- `README.md`
- `package.json`, `pyproject.toml`, or similar project metadata files

After determining the system, collect the following inputs. Use `AskUserQuestion` to ask for all missing values at once. All inputs are optional and can be omitted by the user except where noted.

| Field         | Required | Notes                                                            |
| ------------- | -------- | ---------------------------------------------------------------- |
| `spec.owner`  | Yes      | The owning Group (e.g. `my-team`). Required on every entity.     |
| `spec.domain` | Yes      | The Domain this System belongs to. Do not invent — ask the user. |
| `slack-url`   | No       | URL to the system's Slack help channel                           |
| `logs-url`    | No       | URL to the system's logs in Grafana                              |
| `metrics-url` | No       | URL to the system's metrics in Grafana                           |

**Validating `spec.owner` and `spec.domain`:** Both must reference entities that exist in the live catalog. After collecting them from the user, they **must** be validated via Glean MCP before writing.

If either cannot be validated, report the issue to the user and ask for a corrected value before continuing.

Determine system-level relations:

- `spec.maintainedBy` (Oura custom extension) — one list item for each GitHub-specific system access group (e.g. `github-<system-name>-admin`, `github-<system-name>-developer`).
- `spec.dependsOn` — one list item for each AWS account the system is deployed to (e.g. `resource:aws-account/<account-name>`). These are cross-system resource refs and **must** be validated via Glean MCP before writing.

### Step 3: Find components (deployable units)

Each independently deployable unit is a Component. Search for:

- Separate application directories: `backend/`, `frontend/`, `api/`, `worker/`, `lambda/`
- `Dockerfile`, serverless configs, CDK app definitions, Kubernetes manifests
- Separate `package.json` or `pyproject.toml` files at non-root paths

For each component, determine `spec.type`:

- `service` — backend server or API
- `website` — frontend application
- `library` — shared code that is not directly deployed
- `app` - mobile application component

For each component, determine relations (see [Defining Relations](#defining-relations) for field semantics and ref formats):

- `spec.providesApis` — one list item for each API the component provides
- `spec.consumesApis` — one list item for each API the component consumes
- `spec.dependsOn` — one list item for each Resource or other Component the component depends on

Leave out any relations that don't exist.

### Step 4: Find APIs

For each component, check whether it exposes an API. Look for:

- OpenAPI / Swagger specs (`openapi.yaml`, `swagger.json`, or similar)
- GraphQL schemas
- gRPC proto files
- AsyncAPI specs

Each discovered API becomes a separate API entity. Set `spec.type` on the API entity to one of: `openapi`, `asyncapi`, `graphql`, `grpc`. If an OpenAPI spec file exists, set `spec.definition` to `$openapi: <github-url-to-spec>`. Also add the API name to `spec.providesApis` on the corresponding Component entity.

### Step 5: Find resources

Search infrastructure definitions (CDK, Pulumi, Terraform) for significant standalone infrastructure. Register only resources that are meaningful on their own:

- Databases → `spec.type: database`
- S3 buckets → `spec.type: s3-bucket`
- SQS queues → `spec.type: sqs-queue`
- DynamoDB tables → `spec.type: dynamodb-table`

Do not enumerate every minor AWS resource — only register what is independently significant.

### Step 6: Detect cross-system relations

Analyze the repository to find dependencies on entities that **belong to other systems** — i.e., not defined in this repository's own `catalog-info.yaml`. For each candidate, validate it against the live Backstage catalog via Glean MCP before writing it into the file.

Relations that are entirely internal to this system (e.g. a component consuming an API defined in the same `catalog-info.yaml`) do not need Glean validation.

#### 6a: Detect candidates from code

Search for cross-system relations in the following places:

**API calls → `spec.consumesApis`**
Look for outbound HTTP calls, gRPC stubs, and SDK clients that target services owned by other teams:

- HTTP client base URLs or host constants (e.g. `https://api.example.internal`, environment variables like `FOO_SERVICE_URL`)
- SDK client instantiations (`new FooClient(...)`, `FooServiceStub(channel)`)
- OpenAPI generated clients imported from external packages
- Service-discovery lookups (Consul, AWS Service Discovery, Kubernetes DNS names like `foo-service.foo-namespace.svc.cluster.local`)

Each candidate is a potential `spec.consumesApis` entry on the consuming Component.

**Software package dependencies → `spec.dependsOn` (component)**
Scan `package.json`, `pyproject.toml`, `go.mod`, `requirements.txt`, and similar manifests for **internal** packages (those published from Oura repositories, e.g. `@oura/foo`, `oura-foo`). Each internal package that has its own Backstage Component entity is a potential `spec.dependsOn` entry.
Ignore external open-source packages (e.g. `react`, `boto3`, `fastapi`).

**Infrastructure dependencies → `spec.dependsOn` (resource)**
Inspect CDK, Pulumi, Terraform, and serverless configs for cross-stack/cross-system references:

- SSM Parameter Store reads of parameters owned by another system (e.g. `ssm.StringParameter.fromStringParameterName(this, 'Ref', '/other-system/queue-arn')`)
- Hardcoded ARNs or IDs pointing to resources defined in another system
- Environment variable injections of external resource endpoints

Each candidate is a potential `spec.dependsOn` entry on the dependent Component or Resource.

**Documentation references → any relation**
Skim `README.md`, `docs/`, and inline code comments for explicit mentions of other Oura systems or services (e.g. "This service calls the Foo API", "Reads from the Bar DynamoDB table"). Use these as hints to confirm or discover candidates found above, not as the sole source.

#### 6b: Validate each candidate entity ref via Glean MCP

For **every** candidate identified in 6a, validate it using the procedure in [Validating Entity Refs via Glean MCP](#validating-entity-refs-via-glean-mcp). If the entity is not found, do not add the ref — note it as an unresolved dependency and report it to the user in Step 8.

#### 6c: Relation field mapping

| Detected dependency type             | YAML field                                |
| ------------------------------------ | ----------------------------------------- |
| Outbound API call / SDK client       | `spec.consumesApis` on Component          |
| Internal package dependency          | `spec.dependsOn` on Component             |
| Cross-system infrastructure resource | `spec.dependsOn` on Component or Resource |

### Step 7: Write catalog-info.yaml

Write the file following these rules:

**Naming:**

- All `metadata.name` fields must be lowercase kebab-case and match required pattern: `^[a-z][a-z0-9-]{1,61}[a-z0-9]$`.
- System name: matches the main package name (from `pyproject.toml`, `package.json` etc.) or the repository name.
- Component name: descriptive of the unit's role — e.g. `api-server`, `frontend`, `worker`, `common`.
- API name: `<component-name>-api` for a component's primary API, or a more specific name if the component exposes multiple APIs.
- Namespace: leave out in System entity, use the system name on all Component, API, and Resource entities.
- Title: Title Cased, derived from name, abbreviations should be capitalized (e.g. API, ASSA, B2B)

**File structure:**

1. Start with the YAML language server schema comment on line 1:
   ```
   # yaml-language-server: $schema=https://www.schemastore.org/catalog-info.json
   ```
2. Separate every entity document with `---`.
3. Write entities in this order: System first, then Components, then APIs, then Resources.

**Entity counts:**

- Exactly **one System** per repository (unless it is a true multi-system monorepo).
- One **Component** per deployable unit discovered in Step 3.
- One **API** per API discovered in Step 4.
- One **Resource** per significant infrastructure unit discovered in Step 5.

**Namespace:**

- Do not set `metadata.namespace` on the System entity.
- On every new and existing Component, API and Resource entity: MUST SET `metadata.namespace` to the parent system's name (`metadata.name`).

**Annotations — include on the System entity:**

- `backstage.io/techdocs-ref: dir:.` — Only if a `mkdocs.yml` file exists in the repository root.
- `github.com/project-slug: jouzen/<repo-name>` — always

**Annotations — include on Kubernetes-deployed Components:**

- `backstage.io/kubernetes-id: <component-name>`
- `backstage.io/kubernetes-namespace: <system-name>`

**Lifecycle:**

- Use `experimental` for new or unproven systems; `production` for established ones.
- Keep `lifecycle` identical across all entities in the same system.

### Step 8: Post-write report

After writing `catalog-info.yaml`, produce a brief report:

1. **Relations added** — list each validated entity ref that was added and the field it was placed in.
2. **Unresolved dependencies** — list any candidates from Step 6a that could not be validated (entity not found in catalog), with a short description of where the dependency was detected. Ask the user whether to investigate further or omit them.

### Step 9: Validate

Ask the user to validate `catalog-info.yaml` in Backstage: https://backstage.oura.cloud/entity-validation. Fix any errors provided by the user before considering this task complete.

## Hard constraints

These rules are non-negotiable and must never be violated:

- **Never** define `Domain`, `Group`, `Template`, or `User` entity kinds — those are managed elsewhere.
- **Never** invent domain names or group names. Only reference entities that have been confirmed to exist in the catalog via Glean MCP.
- **Never** add `backstage.io/source-template: template:default/system` unless the system was explicitly created via the Backstage scaffolder template.
- **Never** write a cross-system entity ref (in `spec.consumesApis`, `spec.dependsOn`, `spec.owner`, `spec.domain`, or any other relation field) unless it has been validated against the live Backstage catalog via Glean MCP. Guessed or inferred refs must be omitted.
- **Always** use the exact namespace and name returned by the Glean catalog search — do not construct them manually from convention alone. Apply the short-form or full-ref format required by each field as documented in [Defining Relations](#defining-relations).
- Every entity **must** have `apiVersion`, `kind`, `metadata.name`, and `spec`.
- Always use `apiVersion: backstage.io/v1alpha1`.
- The file must be valid YAML with multiple documents separated by `---`.
