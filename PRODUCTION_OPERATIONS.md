# Production operations

## SLOs and observability

- Availability: 99.9% successful non-4xx requests over 30 days.
- Latency: 95% of API requests complete in under 500 ms over 30 days.
- Alerts in `monitoring/alerts.yml` page on target loss and sustained 5xx budget burn; latency is a warning.
- Start the local stack with `docker compose --profile monitoring up`. Grafana is on port 3001 and Jaeger on 16686.
- Applications emit JSON to stdout. In Kubernetes, ship container stdout with the platform Fluent Bit/Vector agent to Elasticsearch/OpenSearch or the cloud logging service. Never put credentials or request bodies in logs. Sentry is enabled only when `SENTRY_DSN` is set.

## Database lifecycle and performance

Run `alembic upgrade head` as a single pre-deployment job, then deploy application pods. CI performs upgrade, schema-drift, downgrade, and re-upgrade checks. Read-only endpoints use `READ_DATABASE_URL` when set; point it at a managed PostgreSQL replica with health-aware failover.

PostgreSQL logs queries slower than 250 ms in Compose. In production enable `pg_stat_statements`, review top total-time queries weekly, and capture `EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON)` only on a staging copy. Never run `ANALYZE` plans for mutating statements against production.

Run `ops/data-lifecycle.sql` monthly after backup. At larger scale, create new time-partitioned order/audit tables, dual-write during migration, and detach old partitions to object storage in Parquet. Feed analytics from the outbox/Kafka into a warehouse (BigQuery, ClickHouse, or Snowflake), rather than running OLAP scans on the primary.

## Backup and recovery

Schedule `ops/backup.sh` daily to encrypted object storage with immutable retention, plus provider PITR/WAL archiving. Keep 7 daily, 5 weekly, and 12 monthly backups unless policy requires more. Test `ops/restore.sh` into an isolated database every month and record achieved RPO/RTO. The restore target must never be the active primary.

## Security and key rotation

Vault is wired through External Secrets in `k8s/vault-external-secret.yaml`. Replace all example hosts/images before deployment. Rotate JWT signing material by accepting old and new key IDs during a short overlap, issue only with the new key, wait for the maximum token TTL, then revoke the old key. Rotate database/Kafka credentials through Vault dynamic credentials where available. CI scans Python dependencies and container images; enable Dependabot/Renovate for update PRs.

## Resilience and events

Order events are written to `outbox_events` in the same transaction as inventory changes. The dispatcher retries with exponential jitter and opens its Kafka circuit after repeated failures. Consumers must deduplicate by `event_id`; Kafka delivery is at-least-once, not magically exactly-once across external side effects. Register `schemas/order-events.avsc` in a schema registry with backward compatibility before enabling producers.

Redis-backed throttling and cache state are shared between replicas. The in-memory limiter exists only as a fail-safe and is per-process. Use ingress/WAF limits as the outer global boundary.
