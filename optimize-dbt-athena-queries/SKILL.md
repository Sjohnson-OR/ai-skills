---
name: optimize-dbt-athena-queries
description: >
  Diagnose and optimize expensive Athena queries in dbt models.
  Use when dbt models scan too many bytes, queries are slow or expensive,
  or time series tables cause redundant scans due to CTE inlining.
---

# Optimize dbt Athena Queries

Autonomously diagnose and optimize expensive Athena queries in dbt models using EXPLAIN, DESCRIBE, and table metadata. Expect 2-4x reduction in bytes scanned. The key insight: **Athena/Trino cannot materialize CTEs** -- every CTE reference gets inlined, so duplicate CTE references cause duplicate table scans.

## When to Use

- dbt model is scanning more bytes than expected
- Time series tables (large) referenced multiple times in one model
- Query costs are high or approaching scan limits
- Optimizing a family of similar models

## Dependencies and Limitations

- **dbt** with an Athena adapter (installed via `poetry`)
- **AWS CLI** authenticated with a profile that can run Athena queries (needed for `DESCRIBE`)
- **Python 3** (standard library only -- `json`, `sys`)
- Assumes a `poetry run dbt ...` workflow with `--profiles-dir=./profiles`
- Athena workgroup `datascientists` and S3 output location are hardcoded in the `run_athena` helper -- adjust for your environment

## Critical Rules

- **Check bytes scanned / scan count after EVERY optimization step.** Never accept a change that adds scans even if it fixes something else.
- **Table size matters most.** Always identify and prioritize the biggest table. Knowing which table is bigger is critical in Athena -- join order and optimization priority depend on it.
- **Be explicit about staging vs prod stats.** Mixing them up leads to wrong optimization priorities.
- **Do not revert earlier optimizations.** In long contexts, explicitly re-state constraints: "Do not add extra scans of X table."

## Step-by-Step Process

### Step 1: Read the dbt model and compile to get raw SQL

Read the model file directly, then compile to get the fully-resolved SQL with all refs/sources expanded:

```bash
# Compile the specific model
poetry run dbt compile --profiles-dir=./profiles -t staging --target-path target-staging -s <my_model>

# Read the compiled SQL from the target directory
cat target-staging/compiled/oura_warehouse/models/<path>/<my_model>.sql
```

The compiled SQL lives at `target-staging/compiled/oura_warehouse/models/` mirroring the `models/` directory structure.

### Step 2: Gather ALL diagnostic inputs from Athena

Collect **all** of these before beginning optimization. Missing inputs (especially table sizes) leads to wrong priorities.

**Primary tool: `dbt show --inline`** for running any Athena query:

```bash
poetry run dbt show --profiles-dir=./profiles \
  --inline "<SQL_QUERY>" \
  --limit <N> \
  --output json 2>/dev/null | tail -n +8
```

`dbt show` notes:
- Never use `LIMIT` inside the SQL -- always use `--limit` flag
- Output is `{"show": [...]}` JSON -- the `tail -n +8` strips dbt header lines
- To parse: read file, prepend `{` to the text (since `tail` cuts the opening brace), then `json.loads(text)['show']`
- Always use `--output json` -- text output truncates column values

**Exception: DESCRIBE requires AWS CLI** because `dbt show` appends `LIMIT` which is invalid after `DESCRIBE`:

```bash
run_athena() {
  local query=""
  local profile="${2:-oura-production}"
  local region="eu-central-1"
  local output_location="s3://aws-athena-query-results-900155202280-eu-central-1/dbt/"
  local qid=$(aws athena start-query-execution --query-string "$query" \
    --work-group datascientists \
    --result-configuration "OutputLocation=$output_location" \
    --region "$region" --profile "$profile" \
    --output text --query 'QueryExecutionId' 2>&1)
  for i in {1..60}; do
    local state=$(aws athena get-query-execution --query-execution-id "$qid" \
      --region "$region" --profile "$profile" \
      --output text --query 'QueryExecution.Status.State' 2>&1)
    if [[ "$state" == "SUCCEEDED" ]]; then
      aws athena get-query-results --query-execution-id "$qid" \
        --region "$region" --profile "$profile" --output json 2>&1
      return 0
    elif [[ "$state" == "FAILED" ]]; then
      aws athena get-query-execution --query-execution-id "$qid" \
        --region "$region" --profile "$profile" \
        --output json --query 'QueryExecution.Status.StateChangeReason' 2>&1
      return 1
    fi
    sleep 2
  done
}
```

Parse AWS CLI results with:
```python
import json, sys
data = json.load(sys.stdin)
for row in data.get('ResultSet',{}).get('Rows',[]):
    print('\t'.join([d.get('VarCharValue','') for d in row.get('Data',[])]))
```

**Collect all of these in parallel:**

| Input | How to get it | Why it matters |
|-------|--------------|----------------|
| Compiled SQL | From Step 1 | The actual query to optimize |
| EXPLAIN results | `dbt show --inline "EXPLAIN <SQL with hardcoded dates>"` | Shows scan count, join order, partition pruning |
| DESCRIBE for each table | `run_athena "DESCRIBE <schema>.<table>"` (AWS CLI only) | Shows columns, types, and **partition spec** |
| Table sizes | `dbt show --inline "SELECT COUNT(*) FROM <table> WHERE <partition_filter>"` | **Biggest table = highest priority to optimize** |
| Cardinality | `dbt show --inline "SELECT COUNT(*), COUNT(DISTINCT user_id) FROM <table> WHERE ..."` | Helps understand join fan-out |

For EXPLAIN, replace `__PERIOD_FILTER__` and `__OFFSET_PERIOD_FILTER__` with hardcoded date ranges for a 1-day window.

### Step 3: Analyze the EXPLAIN output

Count table scans by searching for `Scan` lines in the EXPLAIN output. Each `ScanFilter` or `ScanFilterProject` fragment represents one physical table scan.

```python
# Count scans per table
for line in explain_lines:
    if 'ScanFilter' in line:
        # Extract table name from the line
        print(line)
```

**What to look for:**
- **Redundant CTE scans** -- biggest issue; CTEs get inlined, so 2 references = 2 scans of underlying tables
- **Missing partition pruning** -- check that partition constraints appear in `constraint on [day]`
- **Join order issues** -- small table should drive large table joins
- **Unnecessary columns** -- `SELECT *` from large tables scans all columns

### Step 4: Apply optimizations directly to the dbt model

**Edit the dbt model file directly** -- don't work with raw SQL then convert back. The optimization happens at the dbt level.

The most common fix: **carry metadata columns through the pipeline** to eliminate re-joins to CTEs that reference large tables.

Pattern -- before (CTE referenced twice = 2x scans):
```sql
WITH big_cte AS (SELECT ... FROM big_table ...),
computed AS (SELECT id, agg_stuff FROM big_cte GROUP BY id)
SELECT computed.*, big_cte.metadata_col  -- re-references big_cte!
FROM computed JOIN big_cte ON ...
```

Pattern -- after (CTE referenced once):
```sql
WITH big_cte AS (SELECT ... FROM big_table ...),
computed AS (
  SELECT id, MIN(metadata_col) AS metadata_col, agg_stuff
  FROM big_cte GROUP BY id  -- carry metadata through
)
SELECT * FROM computed  -- no re-join needed
```

Use `MIN()` for metadata columns that are constant per group (e.g., workout attributes). This is safe and universally supported in Athena/Trino.

### Step 5: Verify scan reduction with EXPLAIN

Recompile the model and run EXPLAIN again on the optimized SQL:

```bash
poetry run dbt compile --profiles-dir=./profiles -t staging --target-path target-staging -s <my_model>
```

Then run EXPLAIN on the new compiled SQL and count scans. **Confirm the target tables now appear only once.** If any table gained a scan, reject the change and try a different approach.

### Step 6: Validate results match

Run both original and optimized queries for the same date range via `dbt show`, then compare programmatically:

```bash
# Run both in parallel (background)
poetry run dbt show --profiles-dir=./profiles --inline "<ORIGINAL_SQL>" \
  --limit 500 --output json 2>/dev/null | tail -n +8 > /tmp/original_results.json

poetry run dbt show --profiles-dir=./profiles --inline "<OPTIMIZED_SQL>" \
  --limit 500 --output json 2>/dev/null | tail -n +8 > /tmp/optimized_results.json
```

Compare with Python:
```python
import json

def load_dbt_json(path):
    with open(path) as f:
        text = '{' + f.read().strip()
    return json.loads(text)['show']

orig = load_dbt_json('/tmp/original_results.json')
opt = load_dbt_json('/tmp/optimized_results.json')

orig_by_id = {r['<primary_key>']: r for r in orig}
opt_by_id = {r['<primary_key>']: r for r in opt}

diffs = 0
for key in set(orig_by_id) & set(opt_by_id):
    for col in orig_by_id[key]:
        if str(orig_by_id[key][col]) != str(opt_by_id[key][col]):
            diffs += 1
            print(f'DIFF {key} {col}: {orig_by_id[key][col]} vs {opt_by_id[key][col]}')

print('ALL MATCH' if diffs == 0 else f'{diffs} differences found')
```

**Watch out for row count differences.** If the optimized query returns fewer rows, check whether the original had duplicate primary keys caused by non-unique joins (e.g., upstream table has multiple rows per ID). This is a **bug in the original** that the optimization may fix -- verify with:

```sql
SELECT COUNT(*), COUNT(DISTINCT <primary_key>) FROM <cte_name>
```

**`id` is often not unique** -- use `id + user_id` as the composite key, especially in staging where test data has duplicate ids.

### Step 7: Test in staging, then prod

```bash
# Staging first -- short date range
poetry run dbt run --profiles-dir=./profiles -t staging_dev -s <my_model> \
  --vars '{"model_start_date": "<recent_date>", "model_stop_date": "<recent_date+1>"}'

# Then prod for a short window
poetry run dbt run --profiles-dir=./profiles -t production_dev -s <my_model> \
  --vars '{"model_start_date": "<recent_date>", "model_stop_date": "<recent_date+1>"}'
```

### Step 8: Handle prod-specific failures

Prod has outliers staging doesn't -- workouts spanning multiple days or years, corrupt data, extreme edge cases. Copy-paste the full error and investigate.

Common prod issue: `INVALID_FUNCTION_ARGUMENT: result of sequence function must not have more than 50000 entries` -- means a workout has an unreasonably long duration. Solution: add a duration cap filter (e.g., workouts > 24 hours).

### Step 9: Apply to similar models

Once the pattern is established, apply the same optimizations to similar models in the same directory.

**WARNING: Explicitly re-verify each model.** In long contexts, the assistant can forget optimizations or fixes it found earlier. When applying to multiple models:
- Re-state the constraints each time: "Do not add extra scans of the time series table"
- Check EXPLAIN scan count for every model, not just the first
- If quality degrades across many models, start a fresh context with the proven pattern documented

## Common Optimization Patterns

| Problem | Solution |
|---------|----------|
| CTE referenced N times | Carry needed columns through pipeline, eliminate re-joins |
| `SELECT *` from large table | Select only needed columns |
| Missing partition filter | Add partition column filter as early as possible |
| Join with large table on wrong side | Put small table as the build side (left in INNER JOIN) |
| Duplicate output rows from non-unique joins | Use GROUP BY with MIN() for metadata -- fixes the bug and optimizes |

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Not collecting table sizes upfront | Always get sizes first -- biggest table = optimization priority |
| Providing prod stats when staging is needed (or vice versa) | Be explicit about which environment each stat comes from |
| Accepting fix that adds a scan elsewhere | Check scan count after every change, not just at the end |
| Trusting `id` as unique key in validation | Use `id + user_id` composite key |
| Assuming staging covers all edge cases | Always run prod validation before declaring done |
| Reverting earlier optimizations in later iterations | Explicitly re-state constraints when context grows large |

## Failure Modes

- **`dbt compile` fails**: Check that the model name and profiles directory are correct. Ensure dbt dependencies are installed (`poetry install`).
- **`dbt show` hangs or times out**: Athena queries on large tables without partition filters can run indefinitely. Always include partition filters.
- **AWS CLI auth errors**: Ensure your AWS profile is configured and has Athena permissions. Run `aws sts get-caller-identity --profile <profile>` to verify.
- **EXPLAIN shows no improvement**: The query may already be optimal, or the bottleneck is elsewhere (e.g., network, Athena queue). Check if partition pruning is effective.
- **Results mismatch after optimization**: The optimization changed query semantics. Revert and try a different approach. Check for non-unique joins that may have been silently producing duplicates.

## Example Interaction

```
User: This dbt model is scanning way too many bytes. Can you optimize it?
  models/workouts/int_workout_metrics.sql