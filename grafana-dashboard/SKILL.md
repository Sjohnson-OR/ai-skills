---
name: grafana-dashboard
description: >
  Create a new Grafana dashboard as JSON committed to the repository.
  Use when the user asks to create or add a Grafana dashboard, set up
  monitoring, observability, or alerting for a service, track a metric,
  add a panel, or visualize data in Grafana.
allowed-tools: Read, Glob, Grep, Write, AskUserQuestion, mcp__grafana__list_datasources, mcp__grafana__search_dashboards, mcp__grafana__list_prometheus_metric_names, mcp__grafana__list_prometheus_label_names, mcp__grafana__list_prometheus_label_values, mcp__grafana__query_prometheus, mcp__grafana__list_loki_label_names, mcp__grafana__query_loki_logs, mcp__grafana__list_cloudwatch_namespaces, mcp__grafana__list_cloudwatch_metrics, mcp__grafana__list_cloudwatch_dimensions, mcp__grafana__query_cloudwatch
---

# Grafana Dashboard

Create a new Grafana dashboard as a JSON file committed to the repository,
with an optional Kubernetes ConfigMap for GitOps deployment.

## When to use this skill

Use this skill when the user asks to:

- Create or add a Grafana dashboard
- Set up monitoring, observability, or alerting for a service
- Track a metric, add a panel, or visualize data in Grafana

This skill uses the **Grafana MCP server at `https://grafana-mcp.oura.cloud/mcp`**
(tool prefix: `mcp__grafana__`). If you have multiple MCP servers connected, use
the one whose tools are prefixed with `mcp__grafana__` — do not use any other
observability or metrics MCP server for this skill.

## Prerequisites

Verify that the Grafana MCP server is available by checking whether
`mcp__grafana__list_datasources` is listed among your tools.

If it is **not** available, stop immediately and instruct the user:

> **Action required — Grafana MCP not connected.**
> This skill uses the Grafana MCP server to discover metrics and validate queries.
> Connect it for your tool:
>
> **Claude Code**
>
> ```bash
> claude mcp add grafana -t http -s user https://grafana-mcp.oura.cloud/mcp
> ```
>
> Then restart the session and run `/mcp` to confirm the connection.
>
> **Cursor**
>
> Add to `~/.cursor/mcp.json`:
>
> ```json
> {
>   "mcpServers": {
>     "grafana": {
>       "url": "https://grafana-mcp.oura.cloud/mcp"
>     }
>   }
> }
> ```
>
> Then reload Cursor.
>
> **Gemini CLI**
>
> ```bash
> gemini mcp add --transport http grafana https://grafana-mcp.oura.cloud/mcp
> ```
>
> Then restart the session.

## Workflow

### Step 1 — Discover Grafana Context

Before asking the user anything, discover Grafana context in two phases.

**Phase A — run in parallel:**

1. **List datasources** — call `mcp__grafana__list_datasources` with no filters.
   Record each datasource's `name`, `uid`, and `type`. You will use these UIDs
   when writing panel `datasource` references — never invent UIDs.

   For CloudWatch specifically:
   - Collect **all** datasources whose `type` is `cloudwatch` (there may be
     several — one per AWS account/environment).
   - For each, note whether its name contains an environment-like word
     (e.g. `dev`, `staging`, `prod`, `production`). If two or more CloudWatch
     datasources map to distinct environment names, record the correspondence
     (e.g. `{ "dev": "<uid-dev>", "production": "<uid-prod>" }`) — this
     enables automatic environment→account switching in Step 5.
   - If only one CloudWatch datasource exists, call
     `mcp__grafana__list_cloudwatch_dimensions` with namespace `AWS/Lambda` (or
     any namespace likely present) to check whether cross-account dimension
     values like `accountId` are exposed. If they are, record the account IDs
     found — these can be used as a variable.

2. **Search existing dashboards** — call `mcp__grafana__search_dashboards` with
   a query derived from the service or topic name in the user's request (e.g. if
   the user said "add monitoring for the payments service", query `"payments"`).
   - If results are found: report each found dashboard's title and URL (or UID if
     URL is not available). Ask whether to proceed with a new dashboard or whether
     to extend one of the existing ones instead. Extending an existing dashboard
     is **out of scope** for this skill — if the user wants that, stop here and
     inform them.
   - If no results: proceed.

**Phase B — run only if Phase A did not trigger a stop:**

3. **Discover environment, cluster, and region labels** — first, identify
   infrastructure metrics to use as an anchor. Use the first metric returned by
   `mcp__grafana__list_prometheus_metric_names` that matches the service name, or
   fall back to `up` if none is found. Then call
   `mcp__grafana__list_prometheus_label_names` scoped to that metric to get only
   the labels that actually exist on the service's metrics (rather than all labels
   across the entire datasource).

   From the returned label names, identify:

   - **Environment label** — the first match among `env`, `environment`,
     `deployment_environment`, `stage` (in that priority order). Record the label
     name and the anchor metric name — both are used to build `label_values()`
     queries in Step 5. Call `mcp__grafana__list_prometheus_label_values` for
     this label to preview values for the Step 1 summary (e.g.
     `["dev", "staging", "production"]`).

   - **Cluster label** — look for a label named `cluster`, `k8s_cluster`,
     `kubernetes_cluster`. If found, call `mcp__grafana__list_prometheus_label_values`
     for it. Only expose as a variable if there are 2 or more distinct values.
     Record the label name for use in Step 5.

   - **Region label** — look for a label named `region`, `cloud_region`,
     `availability_zone`, `az`. If found, call
     `mcp__grafana__list_prometheus_label_values` for it. Only expose as a
     variable if there are 2 or more distinct values. Record the label name for
     use in Step 5.

   If no environment label is found among the candidates, use `env` as the default
   and note it may need adjustment in Step 2.

4. **Discover relevant infrastructure metrics** — if a Prometheus datasource was
   found in Phase A, call `mcp__grafana__list_prometheus_metric_names`, passing the
   service name as the search/filter value to narrow results (the tool's own
   parameter description will guide the exact field name). From the results,
   identify likely-useful metrics by pattern:
   - `*_requests_total` or `*_http_requests_total` → request rate panel (counter → `rate()`)
   - `*_errors_total` or `*_request_errors_total` → error rate panel
   - `*_duration_seconds` (histogram) → latency panel (`histogram_quantile(0.99, ...)`)
   - `*_up` or `up{job="..."}` → service health stat panel
   - If none of these patterns match, list the top 10 discovered metrics and let
     the user choose.

   If no Prometheus datasource was found in Phase A, skip metric discovery and
   note to the user that they will need to supply panel queries manually in Step 2.

5. **Scan codebase for business metrics** — use `Grep` to find metric
   registrations in the codebase. Run these searches (all can run in parallel):
   - Python (prometheus_client): `Counter\(|Gauge\(|Histogram\(|Summary\(` in `*.py` files
   - Go: `prometheus\.New(Counter|Gauge|Histogram)|promauto\.New` in `*.go` files
   - Java/Kotlin: `Counter\.builder\(|Gauge\.builder\(|Timer\.builder\(` in `*.java`, `*.kt` files
   - Node.js: `new Counter\(|new Gauge\(|new Histogram\(` in `*.ts`, `*.js` files
   - Rust: `counter!\(|gauge!\(|histogram!\(|describe_counter!\(|describe_gauge!\(|describe_histogram!\(` in `*.rs` files (covers the `metrics` crate macros)
   - OpenTelemetry (any language): `meter\.(create_counter|create_gauge|create_histogram|create_observable)|getMeter\(|createCounter\(|createHistogram\(|createGauge\(|createObservableGauge\(` in `*.py`, `*.go`, `*.ts`, `*.js`, `*.java`, `*.kt`, `*.rs` files

   For each match, extract the metric name (the string literal passed as the
   first argument or `name:` field). For OpenTelemetry, the metric name is
   typically the first string argument to `create_counter()`/`createCounter()`
   etc. For Rust `metrics` crate macros, it is the first string literal inside
   the macro invocation (e.g. `counter!("orders.placed", 1)`).

   Exclude metrics that match infrastructure patterns already covered above
   (`*_requests_total`, `*_errors_total`, `*_duration_seconds`, `*_up`).
   The remaining metrics are business metrics — things like `orders_placed_total`,
   `payments_succeeded_total`, `active_subscriptions`,
   `feature_flag_evaluations_total`.

   **Note on naming conventions:** OpenTelemetry metrics often use dot-separated
   names (e.g. `orders.placed`) which Prometheus exporters convert to underscores
   (`orders_placed_total`). When validating these metrics in Step 3, search
   Prometheus for both the original name and the underscore variant.

   For each discovered business metric, suggest an appropriate panel:
   - Counter metrics (`*_total`, or OTel counters) → `timeseries` showing `rate()` over time
   - Gauge metrics (no `_total` suffix, e.g. `active_subscriptions`) → `stat` showing current value
   - Histogram metrics → `timeseries` showing `histogram_quantile(0.99, ...)`

6. **Scan infrastructure code for AWS resources** — only run if a `cloudwatch`
   datasource was found in Phase A. Use `Glob` to find CDK, Pulumi, and
   Terraform files, then `Grep` each for AWS resource definitions:

   - CDK (`*.ts`, `*.py` under `cdk/`, `infra/`, `infrastructure/`, `lib/`):
     grep for `new aws\.(lambda|sqs|sns|dynamodb|rds|ecs|apigateway|elb|elbv2|s3|kinesis|stepfunctions|elasticache)\b`
   - Pulumi (`*.ts`, `*.py` under `pulumi/`, `infra/`, `infrastructure/`):
     grep for `new aws\.(lambda|sqs|sns|dynamodb|rds|ecs|apigateway|lb|s3|kinesis|sfn|elasticache)\b`
   - Terraform (`*.tf`):
     grep for `resource\s+"aws_(lambda_function|sqs_queue|sns_topic|dynamodb_table|db_instance|ecs_service|api_gateway|lb|s3_bucket|kinesis_stream|sfn_state_machine|elasticache_cluster)"`

   For each resource found, extract the logical name or resource name identifier
   from the code (the string passed as the name/id argument). Record resource
   type and name.

   Map each resource type to the CloudWatch panels to suggest:

   | Resource type | CloudWatch namespace | Key metrics → panel type |
   |---|---|---|
   | Lambda | `AWS/Lambda` | `Invocations` (timeseries rate), `Errors` (timeseries rate), `Duration` p99 (timeseries), `Throttles` (timeseries), `ConcurrentExecutions` (stat) |
   | SQS | `AWS/SQS` | `NumberOfMessagesSent` (timeseries rate), `ApproximateNumberOfMessagesVisible` (timeseries), `ApproximateAgeOfOldestMessage` (stat — alert-worthy) |
   | DynamoDB | `AWS/DynamoDB` | `ConsumedReadCapacityUnits` (timeseries), `ConsumedWriteCapacityUnits` (timeseries), `SuccessfulRequestLatency` (timeseries), `SystemErrors` (timeseries) |
   | RDS | `AWS/RDS` | `CPUUtilization` (timeseries), `DatabaseConnections` (timeseries), `FreeStorageSpace` (stat), `ReadLatency` (timeseries), `WriteLatency` (timeseries) |
   | ECS / Fargate | `AWS/ECS` | `CPUUtilization` (timeseries), `MemoryUtilization` (timeseries) |
   | API Gateway | `AWS/ApiGateway` | `Count` (timeseries rate), `4XXError` (timeseries), `5XXError` (timeseries), `Latency` p99 (timeseries) |
   | ALB | `AWS/ApplicationELB` | `RequestCount` (timeseries rate), `HTTPCode_Target_4XX_Count` (timeseries), `HTTPCode_Target_5XX_Count` (timeseries), `TargetResponseTime` (timeseries) |
   | S3 | `AWS/S3` | `NumberOfObjects` (stat), `BucketSizeBytes` (stat) |
   | Kinesis | `AWS/Kinesis` | `IncomingRecords` (timeseries rate), `GetRecords.IteratorAgeMilliseconds` (timeseries — alert-worthy) |
   | ElastiCache | `AWS/ElastiCache` | `CPUUtilization` (timeseries), `CurrConnections` (timeseries), `CacheHits` / `CacheMisses` (timeseries) |
   | Step Functions | `AWS/States` | `ExecutionsStarted` (timeseries rate), `ExecutionsFailed` (timeseries), `ExecutionThrottled` (timeseries), `ExecutionTime` (timeseries) |

   If the resource has no discoverable name (e.g. name is derived from a variable
   or `cdk.Fn.importValue`), use a placeholder dimension value and add a note that
   the user will need to fill in the actual resource name.

Summarise findings to the user before proceeding to Step 2:
- Which datasources are available (names only, not UIDs)
- Whether any existing dashboards were found
- The environment label name and values discovered; cluster and region labels if found (with value counts)
- Which infrastructure panels you are suggesting, based on discovered metrics
- Which business metric panels you are suggesting, based on codebase scan
- Which AWS CloudWatch panels you are suggesting, grouped by resource type (or a note that no CloudWatch datasource was found)

### Step 2 — Collect Dashboard Requirements

Using the discovered context, call `AskUserQuestion` once to collect:

- **Dashboard title** — a short human-readable name (e.g. "Payments Service Overview")
- **Description** — one sentence describing what the dashboard monitors
- **Panels** — confirm the suggested panels from Step 1 (both infrastructure and
  business metric panels). Let the user add, remove, or modify any panel. For each
  panel collect:
  - Panel title
  - Metric or LogQL query (pre-fill with the suggested query from Step 1)
  - Visualization type: `timeseries` (default), `stat`, or `table`
- **Environment variable** — confirm the environment label name and values
  discovered in Step 1 (e.g. label `env`, values `dev / staging / production`).
  Let the user correct the label name or values if they differ.
- **Cluster / region variables** — if a cluster or region label was found in
  Step 1 with 2+ values, confirm each one. The user can remove any they don't
  want exposed as a variable.
- **Aggregation mode** — ask: "Should panels show an aggregated view of the
  whole deployment, or individual service instances?"
  - *Aggregated* (default): metric panels use `sum(...)` or `avg(...)` across
    all instances — one line per panel.
  - *Per-instance*: metric panels use `sum by (instance) (...)` — one line per
    instance, `legendFormat: "{{instance}}"`.
- **Grafana folder** — where to place the dashboard in Grafana UI. Default to
  the folder used by the most closely related dashboard found in Step 1. Ask
  only if no related dashboard was found.

Do not ask multiple separate questions. Gather all of the above in a single
`AskUserQuestion` call with a structured prompt listing each item.

### Step 3 — Validate Panel Queries

For **every** panel query collected in Step 2, run these checks before writing
any files:

**For Prometheus (PromQL) queries:**

1. Confirm the base metric name exists:
   ```
   mcp__grafana__list_prometheus_metric_names  (filter: the metric name)
   ```
2. Confirm required label names exist:
   ```
   mcp__grafana__list_prometheus_label_names  (metric: the metric name)
   ```
3. Confirm required label values exist for any label selectors used in the query:
   ```
   mcp__grafana__list_prometheus_label_values  (metric: the metric name, label: the label name)
   ```
4. Run a dry-run range query to confirm data is returned:
   ```
   mcp__grafana__query_prometheus  (expr: the full PromQL, start: now-1h, end: now, step: 5m)
   ```

**For CloudWatch panels:**

1. Confirm at least one `cloudwatch` datasource exists (recorded in Step 1
   Phase A). If not, skip all CloudWatch panels and inform the user.

2. For each resource found in the IaC scan, validate it exists in CloudWatch
   using the datasource UID from Step 1 (use the production datasource if
   multiple account datasources are available):

   a. Confirm the namespace is present:
      ```
      mcp__grafana__list_cloudwatch_namespaces  (datasourceUid: <uid>)
      ```
      If the expected namespace (e.g. `AWS/Lambda`) is not in the list, skip
      panels for that resource type and report it to the user.

   b. Confirm the metric exists within the namespace:
      ```
      mcp__grafana__list_cloudwatch_metrics  (datasourceUid: <uid>, namespace: <namespace>)
      ```

   c. Confirm the dimension key and value exist:
      ```
      mcp__grafana__list_cloudwatch_dimensions  (datasourceUid: <uid>, namespace: <namespace>, metricName: <metric>)
      ```
      If the resource name extracted from IaC is a CDK/Pulumi token or
      `Fn.importValue`, look for a matching real value in the returned dimension
      values. If no match, use the IaC name as a placeholder and flag it.

   d. Run a dry-run query to confirm data is returned:
      ```
      mcp__grafana__query_cloudwatch  (datasourceUid: <uid>, namespace: <namespace>, metricName: <metric>, dimensions: {<key>: <value>}, statistic: "Sum", period: 300)
      ```
      If the query returns no data, note this to the user but do not drop the
      panel — the resource may exist but have no recent activity.

**For Loki (LogQL) queries:**

1. Confirm the stream label exists:
   ```
   mcp__grafana__list_loki_label_names
   ```
   Verify that the label referenced in the query appears in the returned list.
2. Run a dry-run log query:
   ```
   mcp__grafana__query_loki_logs  (query: the LogQL, limit: 5)
   ```

**If validation fails for a panel:**
- Report the failure to the user, including the metric name and error message.
- Ask the user to choose:
  a. Provide a corrected metric name or query
  b. Drop this panel
  c. Keep it with a `WARNING: query not validated against live data` comment
     embedded in the panel's `description` field

Do not proceed to Step 4 until every panel is either validated or explicitly
confirmed by the user.

### Step 4 — Discover Output Location

Scan the repository for an existing dashboards directory using `Glob`:

- Patterns to try (in order): `monitoring/dashboards/**/*.json`,
  `dashboards/**/*.json`, `deploy/grafana/**/*.json`,
  `grafana/dashboards/**/*.json`, `**/dashboards/*.json`
- For each match, read the first 5 lines and check for a `"panels"` key —
  this confirms the file is a Grafana dashboard, not unrelated JSON.

If a matching directory is found: use it. Inform the user: "I'll write the
dashboard to `<path>/`."

If no matching directory is found: call `AskUserQuestion` to ask the user
where to place the files.

### Step 5 — Generate Dashboard JSON

Derive `<dashboard-slug>` from the dashboard title: lowercase, spaces and
any character that is not `[a-z0-9]` replaced with `-`, consecutive `-` collapsed
into one, leading/trailing `-` stripped, maximum 40 characters.

Write `<output-dir>/<dashboard-slug>.json` with this structure:

```json
{
  "uid": "<dashboard-slug>",
  "title": "<title from Step 2>",
  "description": "<description from Step 2>",
  "tags": ["<service-name>", "generated"],
  "schemaVersion": 39,
  "version": 1,
  "time": { "from": "now-6h", "to": "now" },
  "refresh": "1m",
  "templating": {
    "list": [
      {
        "name": "datasource",
        "type": "datasource",
        "query": "prometheus",
        "label": "Datasource",
        "hide": 0,
        "current": {}
      },
      {
        "name": "environment",
        "type": "query",
        "label": "Environment",
        "datasource": { "type": "prometheus", "uid": "<uid from Step 1>" },
        "definition": "label_values(<anchor-metric>, <env-label>)",
        "query": {
          "query": "label_values(<anchor-metric>, <env-label>)",
          "refId": "StandardVariableQuery"
        },
        "hide": 0,
        "current": {},
        "refresh": 2,
        "sort": 1,
        "includeAll": false,
        "multi": false
      }
      <if a cluster label was found with 2+ values, append:>
      ,{
        "name": "cluster",
        "type": "query",
        "label": "Cluster",
        "datasource": { "type": "prometheus", "uid": "<uid from Step 1>" },
        "definition": "label_values(<anchor-metric>{<env-label>=\"$environment\"}, <cluster-label>)",
        "query": {
          "query": "label_values(<anchor-metric>{<env-label>=\"$environment\"}, <cluster-label>)",
          "refId": "StandardVariableQuery"
        },
        "hide": 0,
        "current": {},
        "refresh": 2,
        "sort": 1,
        "includeAll": true,
        "multi": true
      }
      <if a region label was found with 2+ values, append:>
      ,{
        "name": "region",
        "type": "query",
        "label": "Region",
        "datasource": { "type": "prometheus", "uid": "<uid from Step 1>" },
        "definition": "label_values(<anchor-metric>{<env-label>=\"$environment\", <cluster-label>=~\"$cluster\"}, <region-label>)",
        "query": {
          "query": "label_values(<anchor-metric>{<env-label>=\"$environment\", <cluster-label>=~\"$cluster\"}, <region-label>)",
          "refId": "StandardVariableQuery"
        },
        "hide": 0,
        "current": {},
        "refresh": 2,
        "sort": 1,
        "includeAll": true,
        "multi": true
      }
    ]
  },
  "panels": [
    <one panel object per validated panel — see panel structure below>
  ]
}
```

`<service-name>` is the service or topic name derived from the user's request (e.g. the name used
as the metric filter in Step 1). If no service name is identifiable, use the dashboard slug instead.

The `environment` variable is **always** present. Add `cluster` and `region`
variables only if discovered in Step 1 with 2+ values and confirmed in Step 2.
Variables are chained: `cluster` filters by `$environment`; `region` filters by
both `$environment` and `$cluster`. Replace `<anchor-metric>`, `<env-label>`,
`<cluster-label>`, and `<region-label>` with the actual names recorded in Step 1.

**Environment → AWS account mapping** — add one of the following patterns
depending on what was found in Step 1:

*Pattern A — multiple CloudWatch datasources, one per environment* (preferred):
Add a `datasource` type variable for CloudWatch. Grafana will populate the
dropdown with all matching datasources; the user selects the account that
corresponds to the active environment:

```json
{
  "name": "cloudwatch_account",
  "type": "datasource",
  "label": "AWS Account",
  "pluginId": "cloudwatch",
  "regex": "<optional regex to filter datasource names, e.g. cloudwatch-.* — leave empty to show all>",
  "hide": 0,
  "current": {},
  "refresh": 1
}
```

Use `"uid": "${cloudwatch_account}"` in every CloudWatch panel's `datasource`
field. The user can then switch accounts by picking a datasource that corresponds
to the environment they are viewing.

If the datasource names contain environment-like words (e.g. `cloudwatch-dev`,
`cloudwatch-prod`), set `regex` to `cloudwatch-.*` to restrict the variable to
only CloudWatch datasources and add an instructional note in the dashboard
description: "Select the AWS account for the chosen environment."

*Pattern B — single CloudWatch datasource with cross-account access*:
If Step 1 found cross-account dimension values (`accountId`), add a `custom`
variable listing the discovered account IDs and label them with their environment
names where the mapping is known:

```json
{
  "name": "aws_account",
  "type": "custom",
  "label": "AWS Account",
  "hide": 0,
  "query": "<account-id-dev> : dev,<account-id-staging> : staging,<account-id-prod> : production",
  "options": [
    { "selected": false, "text": "dev", "value": "<account-id-dev>" },
    { "selected": false, "text": "staging", "value": "<account-id-staging>" },
    { "selected": true,  "text": "production", "value": "<account-id-prod>" }
  ],
  "current": { "selected": true, "text": "production", "value": "<account-id-prod>" },
  "includeAll": false,
  "multi": false
}
```

Add `"accountId": "$aws_account"` to every CloudWatch panel target alongside
`"region": "default"`.

*Pattern C — single datasource, no cross-account data*:
Skip the account variable. Use the single CloudWatch datasource UID directly in
all panels. Note in the dashboard description which AWS account the panels target.

Add all active label selectors to every panel query. Use `=~` for multi-value
variables (cluster, region) and `=` for single-value ones (environment):
- PromQL: `rate(payments_requests_total{env="$environment", cluster=~"$cluster", region=~"$region"}[5m])`
- LogQL: `{app="payments", env="$environment", cluster=~"$cluster"}`

Omit selectors for variables that were not added to `templating`.

**Aggregation mode** (from Step 2):
- *Aggregated*: wrap the metric expression in `sum(...)` (counters/histograms) or
  `avg(...)` (gauges). `legendFormat` should be the panel title (a static string).
  Example: `sum(rate(payments_requests_total{env="$environment"}[5m]))`
- *Per-instance*: use `sum by (instance) (...)`. Set `legendFormat: "{{instance}}"`.
  Example: `sum by (instance) (rate(payments_requests_total{env="$environment"}[5m]))`

Omit the `datasource` templating variable if all panels use the same datasource.
If panels use multiple datasource types (e.g. Prometheus and Loki), include one
datasource variable per type.

**Panel structure — CloudWatch:**

```json
{
  "id": <sequential integer>,
  "type": "timeseries",
  "title": "<metric title, e.g. 'Lambda Errors'>",
  "description": "",
  "datasource": { "type": "cloudwatch", "uid": "<cloudwatch-uid from Step 1>" },
  "gridPos": { "h": 8, "w": 12, "x": <0 or 12 alternating>, "y": <current y> },
  "targets": [
    {
      "refId": "A",
      "datasource": { "type": "cloudwatch", "uid": "<cloudwatch-uid from Step 1>" },
      "queryMode": "Metrics",
      "metricQueryType": 0,
      "metricEditorMode": 0,
      "namespace": "<AWS namespace, e.g. AWS/Lambda>",
      "metricName": "<metric name, e.g. Errors>",
      "statistic": "<Sum|Average|Maximum|p99 — see table above>",
      "dimensions": { "<dimension key, e.g. FunctionName>": "<resource name from IaC>" },
      "region": "default",
      "period": "",
      "matchExact": true,
      "alias": ""
    }
  ],
  "options": { "legend": { "displayMode": "list", "placement": "bottom" } },
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": null },
          { "color": "yellow", "value": 0.05 },
          { "color": "red", "value": 0.1 }
        ]
      }
    }
  }
}
```

Use `"type": "stat"` and `"h": 4, "w": 6` for stat-type CloudWatch panels from
the table above (e.g. SQS age, RDS free storage, S3 object count).

Dimension keys per resource type:
- Lambda: `FunctionName`
- SQS: `QueueName`
- DynamoDB: `TableName`
- RDS: `DBInstanceIdentifier`
- ECS: `ClusterName` + `ServiceName` (two keys)
- API Gateway: `ApiName`
- ALB: `LoadBalancer`
- S3: `BucketName` + `StorageType`
- Kinesis: `StreamName`
- ElastiCache: `CacheClusterId`
- Step Functions: `StateMachineArn`

**Dashboard rows** — organise panels into labelled rows using `type: "row"` panels.
Suggested row structure (adapt based on which panels exist):

1. **Overview** — `stat` panels for key health signals (service up, error rate %)
2. **Infrastructure** — `timeseries` panels for request rate, latency, error rate
3. **AWS Infrastructure** — CloudWatch panels grouped by resource type (one sub-section per resource; omit entire row if no CloudWatch datasource)
4. **Business Metrics** — panels for business metrics discovered from codebase
5. **Logs** — log panel (if Loki datasource available)

Row panel structure:
```json
{
  "id": <sequential integer>,
  "type": "row",
  "title": "<Row Title>",
  "collapsed": false,
  "gridPos": { "h": 1, "w": 24, "x": 0, "y": <current y> },
  "panels": []
}
```

A row panel occupies `h: 1`. Increment `y` by 1 for the row header, then place
content panels beneath it using the layout rules below.

**Log panel** — include by default if a Loki datasource was found in Step 1.
Place it in the Logs row. Use the most specific stream selector available
(prefer `app` or `service_name` label if present on the Loki datasource):

```json
{
  "id": <sequential integer>,
  "type": "logs",
  "title": "Logs",
  "datasource": { "type": "loki", "uid": "<loki-uid from Step 1>" },
  "gridPos": { "h": 10, "w": 24, "x": 0, "y": <current y> },
  "targets": [
    {
      "expr": "{app=\"<service-name>\", <env-label>=\"$environment\"}",
      "refId": "A"
    }
  ],
  "options": {
    "showTime": true,
    "showLabels": false,
    "wrapLogMessage": true,
    "dedupStrategy": "none",
    "sortOrder": "Descending"
  }
}
```

If the stream selector label is unknown, validate it in Step 3 using
`mcp__grafana__list_loki_label_names` before writing.

**Panel structure — `timeseries` (default):**

```json
{
  "id": <sequential integer starting at 1>,
  "type": "timeseries",
  "title": "<panel title>",
  "description": "<empty, or WARNING comment if query was not validated>",
  "datasource": { "type": "prometheus", "uid": "<uid from Step 1>" },
  "gridPos": { "h": 8, "w": 12, "x": <0 or 12 alternating>, "y": <row * 8> },
  "targets": [
    {
      "expr": "<validated PromQL>",
      "legendFormat": "{{job}}",
      "refId": "A"
    }
  ],
  "options": { "legend": { "displayMode": "list", "placement": "bottom" } },
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": null },
          { "color": "yellow", "value": 0.05 },
          { "color": "red", "value": 0.1 }
        ]
      }
    }
  }
}
```

**Panel structure — `stat`:**

```json
{
  "id": <sequential integer>,
  "type": "stat",
  "title": "<panel title>",
  "description": "<empty, or WARNING string if query was not validated>",
  "datasource": { "type": "prometheus", "uid": "<uid from Step 1>" },
  "gridPos": { "h": 4, "w": 6, "x": <0, 6, 12, or 18>, "y": <row start y> },
  "targets": [
    {
      "expr": "<validated PromQL>",
      "legendFormat": "{{job}}",
      "refId": "A"
    }
  ],
  "options": {
    "legend": { "displayMode": "list", "placement": "bottom" },
    "reduceOptions": { "calcs": ["lastNotNull"] }
  },
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": null },
          { "color": "yellow", "value": 0.05 },
          { "color": "red", "value": 0.1 }
        ]
      }
    }
  }
}
```

**Panel structure — `table`:**

```json
{
  "id": <sequential integer>,
  "type": "table",
  "title": "<panel title>",
  "description": "<empty, or WARNING string if query was not validated>",
  "datasource": { "type": "prometheus", "uid": "<uid from Step 1>" },
  "gridPos": { "h": 8, "w": 24, "x": 0, "y": <row start y> },
  "targets": [
    {
      "expr": "<validated PromQL>",
      "legendFormat": "{{job}}",
      "refId": "A"
    }
  ],
  "options": { "legend": { "displayMode": "list", "placement": "bottom" } },
  "fieldConfig": {
    "defaults": {
      "unit": "short",
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "color": "green", "value": null },
          { "color": "yellow", "value": 0.05 },
          { "color": "red", "value": 0.1 }
        ]
      }
    }
  }
}
```

**Layout rule:**

- `row` panels: `h: 1`, `w: 24`, `x: 0`. Increment `y` by 1 after placing a row header.
- `timeseries` panels: two per row, `w: 12`. First panel `x: 0`, second `x: 12`. Increment `y` by 8 when starting a new row.
- `stat` panels: four per row, `w: 6`. `x` values: 0, 6, 12, 18. Increment `y` by 4 when starting a new row. If the total stat panel count is not a multiple of four, the last partial row still starts at the correct `y`; leave the remaining grid cells empty.
- `table` panels: one per row, `w: 24`, `x: 0`. Increment `y` by 8 when starting a new row.
- `logs` panels: one per row, `w: 24`, `x: 0`, `h: 10`. Increment `y` by 10 when starting a new row.
- Mixed sequences: complete each panel type's row before starting the next type. Carry the current `y` value across type and section changes.

### Step 6 — Optional Kubernetes ConfigMap

Ask the user (via `AskUserQuestion`):
> "Do you want a Kubernetes ConfigMap to deploy this dashboard via GitOps?"

If yes, write `<output-dir>/<dashboard-slug>-configmap.yaml`:

Use the Grafana folder collected in Step 2 as the `grafana_folder` annotation value.
If the user did not specify a folder (it was inferred from an existing dashboard),
use that inferred folder name.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: <dashboard-slug>
  annotations:
    grafana_folder: <Grafana folder from Step 2>
  labels:
    grafana_dashboard: "1"
data:
  <dashboard-slug>.json: |
    <full dashboard JSON, each line indented by 4 spaces>
```

The value under `data.<dashboard-slug>.json` must be the complete, valid
Grafana JSON from Step 5, indented by 4 spaces so it is valid YAML literal
block scalar syntax.

## Hard Constraints

- **Never write a panel query that was not validated** without an explicit user
  confirmation and `WARNING: query not validated against live data` in the
  panel's `description` field.
- **Never invent datasource UIDs.** Always use UIDs returned by
  `mcp__grafana__list_datasources`.
- **Never create a dashboard that duplicates an existing one.** If Step 1 finds
  a closely matching dashboard, report it and stop — extending existing
  dashboards is out of scope for this skill.
- Dashboard JSON must be valid and importable into Grafana without modification.
  `schemaVersion` must match the value in Step 5's template (39). Do not use a lower value.