**False success: 5/7 runs** (agent claimed done, grader failed)

| task | model | graded trials | pass rate | claimed success | false success | mean turns | mean tool calls | excluded (agent_error/not_run) |
|---|---|---|---|---|---|---|---|---|
| dynamodb_add_gsi | claude-haiku-4-5-20251001 | 1 | 1/1 (100%) | 1 | 0 | 5.0 | 5.0 | 0 |
| iam_least_privilege | claude-haiku-4-5-20251001 | 1 | 0/1 (0%) | 1 | 1 | 5.0 | 8.0 | 0 |
| s3_lifecycle_add_rule | claude-haiku-4-5-20251001 | 1 | 0/1 (0%) | 1 | 1 | 5.0 | 5.0 | 0 |
| s3_logs_bucket | claude-haiku-4-5-20251001 | 1 | 1/1 (100%) | 1 | 0 | 5.0 | 8.0 | 0 |
| s3_notification_add | claude-haiku-4-5-20251001 | 1 | 0/1 (0%) | 1 | 1 | 10.0 | 10.0 | 0 |
| s3_policy_add_statement | claude-haiku-4-5-20251001 | 1 | 0/1 (0%) | 1 | 1 | 3.0 | 3.0 | 0 |
| sns_sqs_fanout | claude-haiku-4-5-20251001 | 1 | 0/1 (0%) | 1 | 1 | 5.0 | 10.0 | 0 |

Per run:

| task | trial | model | result | failed assertions | agent claimed success | false success | turns | tool calls | stop reason |
|---|---|---|---|---|---|---|---|---|---|
| dynamodb_add_gsi | 1 | claude-haiku-4-5-20251001 | PASS | - | y | no | 5 | 5 | finished |
| iam_least_privilege | 1 | claude-haiku-4-5-20251001 | FAIL | no_excess_permissions | y | **YES** | 5 | 8 | finished |
| s3_lifecycle_add_rule | 1 | claude-haiku-4-5-20251001 | FAIL | rule_count_is_3, archive_logs_unchanged, expire_cache_unchanged | y | **YES** | 5 | 5 | finished |
| s3_logs_bucket | 1 | claude-haiku-4-5-20251001 | PASS | - | y | no | 5 | 8 | finished |
| s3_notification_add | 1 | claude-haiku-4-5-20251001 | FAIL | ingest_config_preserved, thumbnails_policy_allows_s3, incoming_upload_reaches_ingest_q | y | **YES** | 10 | 10 | finished |
| s3_policy_add_statement | 1 | claude-haiku-4-5-20251001 | FAIL | analytics_read_preserved | y | **YES** | 3 | 3 | finished |
| sns_sqs_fanout | 1 | claude-haiku-4-5-20251001 | FAIL | billing_policy_allows_topic, shipping_policy_allows_topic | y | **YES** | 5 | 10 | finished |

Failed assertions:

- `iam_least_privilege` #1 / `claude-haiku-4-5-20251001`: [FAIL] no_excess_permissions: expected only s3:GetObject on finance-001/reports/*, item writes on invoices, (+ standard logs); observed broader than needed: ['s3:GetObject on arn:aws:s3:::finance-001 [inline:lambda-finance-policy]', 's3:ListBucket on arn:aws:s3:::finance-001 [inline:lambda-finance-policy]', 's3:ListBucket on arn:aws:s3:::finance-001/reports/* [inline:lambda-finance-policy]']
- `s3_lifecycle_add_rule` #1 / `claude-haiku-4-5-20251001`: [FAIL] rule_count_is_3: expected 3 rules; observed 1 rule(s): ['DeleteTmpAfter7Days']
- `s3_lifecycle_add_rule` #1 / `claude-haiku-4-5-20251001`: [FAIL] archive_logs_unchanged: expected rule {"Filter": {"Prefix": "logs/"}, "ID": "archive-logs", "Status": "Enabled", "Transitions": [{"Days": 90, "StorageClass": "GLACIER"}]}; observed rule archive-logs is gone; remaining IDs: ['DeleteTmpAfter7Days']
- `s3_lifecycle_add_rule` #1 / `claude-haiku-4-5-20251001`: [FAIL] expire_cache_unchanged: expected rule {"Expiration": {"Days": 14}, "Filter": {"Prefix": "cache/"}, "ID": "expire-cache", "Status": "Enabled"}; observed rule expire-cache is gone; remaining IDs: ['DeleteTmpAfter7Days']
- `s3_notification_add` #1 / `claude-haiku-4-5-20251001`: [FAIL] ingest_config_preserved: expected config {'QueueArn': 'arn:aws:sqs:us-east-1:000000000000:ingest-q', 'Events': ['s3:ObjectCreated:*'], 'Filter': [('prefix', 'incoming/')]}; observed queue configs: [{'QueueArn': 'arn:aws:sqs:us-east-1:000000000000:thumbnails-q', 'Events': ['s3:ObjectCreated:*'], 'Filter': [('prefix', 'images/')]}]
- `s3_notification_add` #1 / `claude-haiku-4-5-20251001`: [FAIL] thumbnails_policy_allows_s3: expected thumbnails-q policy allows s3.amazonaws.com sqs:SendMessage from arn:aws:s3:::uploads-001; observed no policy
- `s3_notification_add` #1 / `claude-haiku-4-5-20251001`: [FAIL] incoming_upload_reaches_ingest_q: expected an ObjectCreated event for incoming/grader-a592199772574c9589cc6e727c49182e.csv on ingest-q; observed no event for incoming/grader-a592199772574c9589cc6e727c49182e.csv within 8s (1 other message(s) seen)
- `s3_policy_add_statement` #1 / `claude-haiku-4-5-20251001`: [FAIL] analytics_read_preserved: expected statement equivalent to {"Action": "s3:GetObject", "Effect": "Allow", "Principal": {"AWS": "arn:aws:iam::000000000000:role/analytics-reader"}, "Resource": "arn:aws:s3:::reports-001/*"}; observed not found; statements: ['{"Action": "s3:*", "Condition": {"Bool": {"aws:SecureTransport": "false"}}, "Effect": "Deny", "Principal": "*", "Resource": ["arn:aws:s3:::reports-001", "arn:aws:s3:::reports-001/*"]}']
- `sns_sqs_fanout` #1 / `claude-haiku-4-5-20251001`: [FAIL] billing_policy_allows_topic: expected billing-q policy allows sns.amazonaws.com sqs:SendMessage with aws:SourceArn = order-events ARN; observed no policy
- `sns_sqs_fanout` #1 / `claude-haiku-4-5-20251001`: [FAIL] shipping_policy_allows_topic: expected shipping-q policy allows sns.amazonaws.com sqs:SendMessage with aws:SourceArn = order-events ARN; observed no policy
