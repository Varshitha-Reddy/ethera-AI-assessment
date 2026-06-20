-- Run monthly after a verified backup. Tune intervals to legal/business policy.
BEGIN;
CREATE TABLE IF NOT EXISTS order_audit_logs_archive (LIKE order_audit_logs INCLUDING ALL);
WITH moved AS (
  DELETE FROM order_audit_logs
  WHERE changed_at < now() - interval '2 years'
  RETURNING *
)
INSERT INTO order_audit_logs_archive SELECT * FROM moved;

DELETE FROM outbox_events
WHERE published_at IS NOT NULL AND published_at < now() - interval '30 days';
COMMIT;

-- Refresh outside the transaction when CONCURRENTLY is enabled for an OLAP view.
ANALYZE products;
ANALYZE customers;
ANALYZE orders;
