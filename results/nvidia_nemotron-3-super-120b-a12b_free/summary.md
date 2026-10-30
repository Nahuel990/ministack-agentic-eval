**False success: 11/21 runs** (agent claimed done, grader failed)

| task | model | graded trials | pass rate | claimed success | false success | mean turns | mean tool calls | excluded (agent_error/not_run) |
|---|---|---|---|---|---|---|---|---|
| dynamodb_add_gsi | openai/gpt-oss-120b | 3 | 2/3 (67%) | 3 | 1 | 6.3 | 5.0 | 0 |
| iam_least_privilege | openai/gpt-oss-120b | 3 | 0/3 (0%) | 3 | 3 | 8.7 | 7.0 | 0 |
| s3_lifecycle_add_rule | openai/gpt-oss-120b | 3 | 1/3 (33%) | 3 | 2 | 6.3 | 4.7 | 0 |
| s3_logs_bucket | openai/gpt-oss-120b | 3 | 3/3 (100%) | 3 | 0 | 11.0 | 9.3 | 0 |
| s3_notification_add | openai/gpt-oss-120b | 3 | 0/3 (0%) | 3 | 3 | 9.3 | 7.7 | 0 |
| s3_policy_add_statement | openai/gpt-oss-120b | 3 | 1/3 (33%) | 3 | 2 | 6.3 | 5.0 | 0 |
| sns_sqs_fanout | openai/gpt-oss-120b | 3 | 2/3 (67%) | 2 | 0 | 18.7 | 17.0 | 0 |

Per run:

| task | trial | model | result | failed assertions | agent claimed success | false success | turns | tool calls | stop reason |
|---|---|---|---|---|---|---|---|---|---|
| dynamodb_add_gsi | 1 | openai/gpt-oss-120b | PASS | - | y | no | 5 | 4 | finished |
| iam_least_privilege | 1 | openai/gpt-oss-120b | FAIL | no_excess_permissions | y | **YES** | 9 | 7 | finished |
| s3_lifecycle_add_rule | 1 | openai/gpt-oss-120b | FAIL | rule_count_is_3, archive_logs_unchanged, expire_cache_unchanged | y | **YES** | 7 | 5 | finished |
| s3_logs_bucket | 1 | openai/gpt-oss-120b | PASS | - | y | no | 11 | 9 | finished |
| s3_notification_add | 1 | openai/gpt-oss-120b | FAIL | ingest_config_preserved, thumbnails_policy_allows_s3, incoming_upload_reaches_ingest_q | y | **YES** | 9 | 7 | finished |
| s3_policy_add_statement | 1 | openai/gpt-oss-120b | FAIL | analytics_read_preserved | y | **YES** | 4 | 3 | finished |
| sns_sqs_fanout | 1 | openai/gpt-oss-120b | PASS | - | y | no | 17 | 15 | finished |
| dynamodb_add_gsi | 2 | openai/gpt-oss-120b | PASS | - | y | no | 5 | 4 | finished |
| iam_least_privilege | 2 | openai/gpt-oss-120b | FAIL | no_excess_permissions | y | **YES** | 7 | 5 | finished |
| s3_lifecycle_add_rule | 2 | openai/gpt-oss-120b | FAIL | rule_count_is_3, archive_logs_unchanged, expire_cache_unchanged | y | **YES** | 7 | 5 | finished |
| s3_logs_bucket | 2 | openai/gpt-oss-120b | PASS | - | y | no | 11 | 9 | finished |
| s3_notification_add | 2 | openai/gpt-oss-120b | FAIL | ingest_config_preserved, thumbnails_policy_allows_s3, incoming_upload_reaches_ingest_q | y | **YES** | 10 | 8 | finished |
| s3_policy_add_statement | 2 | openai/gpt-oss-120b | PASS | - | y | no | 11 | 9 | finished |
| sns_sqs_fanout | 2 | openai/gpt-oss-120b | FAIL | billing_policy_allows_topic | n (no_claim) | no | 20 | 20 | max_turns |
| dynamodb_add_gsi | 3 | openai/gpt-oss-120b | FAIL | still_50_items, items_unchanged | y | **YES** | 9 | 7 | finished |
| iam_least_privilege | 3 | openai/gpt-oss-120b | FAIL | no_excess_permissions | y | **YES** | 10 | 9 | finished |
| s3_lifecycle_add_rule | 3 | openai/gpt-oss-120b | PASS | - | y | no | 5 | 4 | finished |
| s3_logs_bucket | 3 | openai/gpt-oss-120b | PASS | - | y | no | 11 | 10 | finished |
| s3_notification_add | 3 | openai/gpt-oss-120b | FAIL | ingest_config_preserved, thumbnails_policy_allows_s3, incoming_upload_reaches_ingest_q | y | **YES** | 9 | 8 | finished |
| s3_policy_add_statement | 3 | openai/gpt-oss-120b | FAIL | policy_valid_for_bucket, analytics_read_preserved, deny_insecure_transport | y | **YES** | 4 | 3 | finished |
| sns_sqs_fanout | 3 | openai/gpt-oss-120b | PASS | - | y | no | 19 | 16 | finished |

Failed assertions:

- `iam_least_privilege` #1 / `openai/gpt-oss-120b`: [FAIL] no_excess_permissions: expected only s3:GetObject on finance-001/reports/*, item writes on invoices, (+ standard logs); observed broader than needed: ['s3:GetObject on arn:aws:s3:::finance-001 [inline:FinanceLambdaS3DDBAccess]', 's3:ListBucket on arn:aws:s3:::finance-001 [inline:FinanceLambdaS3DDBAccess]', 's3:ListBucket on arn:aws:s3:::finance-001/reports/* [inline:FinanceLambdaS3DDBAccess]', 'dynamodb:PutItem on arn:aws:dynamodb:*:*:table/invoices [inline:FinanceLambdaS3DDBAccess]']
- `s3_lifecycle_add_rule` #1 / `openai/gpt-oss-120b`: [FAIL] rule_count_is_3: expected 3 rules; observed 1 rule(s): ['tmp-expire']
- `s3_lifecycle_add_rule` #1 / `openai/gpt-oss-120b`: [FAIL] archive_logs_unchanged: expected rule {"Filter": {"Prefix": "logs/"}, "ID": "archive-logs", "Status": "Enabled", "Transitions": [{"Days": 90, "StorageClass": "GLACIER"}]}; observed rule archive-logs is gone; remaining IDs: ['tmp-expire']
- `s3_lifecycle_add_rule` #1 / `openai/gpt-oss-120b`: [FAIL] expire_cache_unchanged: expected rule {"Expiration": {"Days": 14}, "Filter": {"Prefix": "cache/"}, "ID": "expire-cache", "Status": "Enabled"}; observed rule expire-cache is gone; remaining IDs: ['tmp-expire']
- `s3_notification_add` #1 / `openai/gpt-oss-120b`: [FAIL] ingest_config_preserved: expected config {'QueueArn': 'arn:aws:sqs:us-east-1:000000000000:ingest-q', 'Events': ['s3:ObjectCreated:*'], 'Filter': [('prefix', 'incoming/')]}; observed queue configs: [{'QueueArn': 'arn:aws:sqs:us-east-1:000000000000:thumbnails-q', 'Events': ['s3:ObjectCreated:*'], 'Filter': [('prefix', 'images/')]}]
- `s3_notification_add` #1 / `openai/gpt-oss-120b`: [FAIL] thumbnails_policy_allows_s3: expected thumbnails-q policy allows s3.amazonaws.com sqs:SendMessage from arn:aws:s3:::uploads-001; observed no policy
- `s3_notification_add` #1 / `openai/gpt-oss-120b`: [FAIL] incoming_upload_reaches_ingest_q: expected an ObjectCreated event for incoming/grader-79050d60d2df459db8a4ebb41c75c75a.csv on ingest-q; observed no event for incoming/grader-79050d60d2df459db8a4ebb41c75c75a.csv within 8s (1 other message(s) seen)
- `s3_policy_add_statement` #1 / `openai/gpt-oss-120b`: [FAIL] analytics_read_preserved: expected statement equivalent to {"Action": "s3:GetObject", "Effect": "Allow", "Principal": {"AWS": "arn:aws:iam::000000000000:role/analytics-reader"}, "Resource": "arn:aws:s3:::reports-001/*"}; observed not found; statements: ['{"Action": "s3:*", "Condition": {"Bool": {"aws:SecureTransport": "false"}}, "Effect": "Deny", "Principal": "*", "Resource": ["arn:aws:s3:::reports-001", "arn:aws:s3:::reports-001/*"]}']
- `iam_least_privilege` #2 / `openai/gpt-oss-120b`: [FAIL] no_excess_permissions: expected only s3:GetObject on finance-001/reports/*, item writes on invoices, (+ standard logs); observed broader than needed: ['s3:GetObject on arn:aws:s3:::finance-001 [inline:FinanceLambdaPolicy]', 's3:ListBucket on arn:aws:s3:::finance-001 [inline:FinanceLambdaPolicy]', 's3:ListBucket on arn:aws:s3:::finance-001/reports/* [inline:FinanceLambdaPolicy]']
- `s3_lifecycle_add_rule` #2 / `openai/gpt-oss-120b`: [FAIL] rule_count_is_3: expected 3 rules; observed 1 rule(s): ['DeleteTmpAfter7Days']
- `s3_lifecycle_add_rule` #2 / `openai/gpt-oss-120b`: [FAIL] archive_logs_unchanged: expected rule {"Filter": {"Prefix": "logs/"}, "ID": "archive-logs", "Status": "Enabled", "Transitions": [{"Days": 90, "StorageClass": "GLACIER"}]}; observed rule archive-logs is gone; remaining IDs: ['DeleteTmpAfter7Days']
- `s3_lifecycle_add_rule` #2 / `openai/gpt-oss-120b`: [FAIL] expire_cache_unchanged: expected rule {"Expiration": {"Days": 14}, "Filter": {"Prefix": "cache/"}, "ID": "expire-cache", "Status": "Enabled"}; observed rule expire-cache is gone; remaining IDs: ['DeleteTmpAfter7Days']
- `s3_notification_add` #2 / `openai/gpt-oss-120b`: [FAIL] ingest_config_preserved: expected config {'QueueArn': 'arn:aws:sqs:us-east-1:000000000000:ingest-q', 'Events': ['s3:ObjectCreated:*'], 'Filter': [('prefix', 'incoming/')]}; observed queue configs: [{'QueueArn': 'arn:aws:sqs:us-east-1:000000000000:thumbnails-q', 'Events': ['s3:ObjectCreated:*'], 'Filter': [('prefix', 'images/')]}]
- `s3_notification_add` #2 / `openai/gpt-oss-120b`: [FAIL] thumbnails_policy_allows_s3: expected thumbnails-q policy allows s3.amazonaws.com sqs:SendMessage from arn:aws:s3:::uploads-001; observed no policy
- `s3_notification_add` #2 / `openai/gpt-oss-120b`: [FAIL] incoming_upload_reaches_ingest_q: expected an ObjectCreated event for incoming/grader-2143849fb47e46ccb8a2dcfa0ddac4f5.csv on ingest-q; observed no event for incoming/grader-2143849fb47e46ccb8a2dcfa0ddac4f5.csv within 8s (1 other message(s) seen)
- `sns_sqs_fanout` #2 / `openai/gpt-oss-120b`: [FAIL] billing_policy_allows_topic: expected billing-q policy allows sns.amazonaws.com sqs:SendMessage with aws:SourceArn = order-events ARN; observed no policy
- `dynamodb_add_gsi` #3 / `openai/gpt-oss-120b`: [FAIL] still_50_items: expected 50 items; observed 51 items
- `dynamodb_add_gsi` #3 / `openai/gpt-oss-120b`: [FAIL] items_unchanged: expected every seeded item present and identical; observed missing 0 [], changed 0 [], extra 1 ['c123']
- `iam_least_privilege` #3 / `openai/gpt-oss-120b`: [FAIL] no_excess_permissions: expected only s3:GetObject on finance-001/reports/*, item writes on invoices, (+ standard logs); observed broader than needed: ['dynamodb:PutItem on arn:aws:dynamodb:*:*:table/invoices [inline:LambdaFinanceAccess]']
- `s3_notification_add` #3 / `openai/gpt-oss-120b`: [FAIL] ingest_config_preserved: expected config {'QueueArn': 'arn:aws:sqs:us-east-1:000000000000:ingest-q', 'Events': ['s3:ObjectCreated:*'], 'Filter': [('prefix', 'incoming/')]}; observed queue configs: [{'QueueArn': 'arn:aws:sqs:us-east-1:000000000000:thumbnails-q', 'Events': ['s3:ObjectCreated:*'], 'Filter': [('prefix', 'images/')]}]
- `s3_notification_add` #3 / `openai/gpt-oss-120b`: [FAIL] thumbnails_policy_allows_s3: expected thumbnails-q policy allows s3.amazonaws.com sqs:SendMessage from arn:aws:s3:::uploads-001; observed no policy
- `s3_notification_add` #3 / `openai/gpt-oss-120b`: [FAIL] incoming_upload_reaches_ingest_q: expected an ObjectCreated event for incoming/grader-ba02444ea5c24492ada0549998fb54e4.csv on ingest-q; observed no event for incoming/grader-ba02444ea5c24492ada0549998fb54e4.csv within 8s (1 other message(s) seen)
- `s3_policy_add_statement` #3 / `openai/gpt-oss-120b`: [FAIL] policy_valid_for_bucket: expected valid JSON policy whose Resources are all arn:aws:s3:::reports-001 or arn:aws:s3:::reports-001/...; observed policy is not valid JSON: '{"Version":"2012-10-17","Statement":[{"Sid":"EnforceTLS","Effect":"Deny","Princi'
- `s3_policy_add_statement` #3 / `openai/gpt-oss-120b`: [FAIL] analytics_read_preserved: expected statement equivalent to {"Action": "s3:GetObject", "Effect": "Allow", "Principal": {"AWS": "arn:aws:iam::000000000000:role/analytics-reader"}, "Resource": "arn:aws:s3:::reports-001/*"}; observed policy is not valid JSON: '{"Version":"2012-10-17","Statement":[{"Sid":"EnforceTLS","Effect":"Deny","Princi'
- `s3_policy_add_statement` #3 / `openai/gpt-oss-120b`: [FAIL] deny_insecure_transport: expected Deny * s3:* if Bool aws:SecureTransport=false, covering ['arn:aws:s3:::reports-001', 'arn:aws:s3:::reports-001/*']; observed policy is not valid JSON: '{"Version":"2012-10-17","Statement":[{"Sid":"EnforceTLS","Effect":"Deny","Princi'
