**False success: 2/5 runs** (agent claimed done, grader failed)

| task | model | graded trials | pass rate | claimed success | false success | mean turns | mean tool calls | excluded (agent_error/not_run) |
|---|---|---|---|---|---|---|---|---|
| dynamodb_add_gsi | nvidia/nemotron-3-super-120b-a12b:free | 1 | 1/1 (100%) | 1 | 0 | 6.0 | 5.0 | 2 |
| iam_least_privilege | nvidia/nemotron-3-super-120b-a12b:free | 1 | 0/1 (0%) | 1 | 1 | 10.0 | 9.0 | 2 |
| s3_lifecycle_add_rule | nvidia/nemotron-3-super-120b-a12b:free | 1 | 0/1 (0%) | 1 | 1 | 6.0 | 5.0 | 2 |
| s3_logs_bucket | nvidia/nemotron-3-super-120b-a12b:free | 0 | n/a | n/a | n/a | n/a | n/a | 3 |
| s3_notification_add | nvidia/nemotron-3-super-120b-a12b:free | 0 | n/a | n/a | n/a | n/a | n/a | 3 |
| s3_policy_add_statement | nvidia/nemotron-3-super-120b-a12b:free | 0 | n/a | n/a | n/a | n/a | n/a | 3 |
| sns_sqs_fanout | nvidia/nemotron-3-super-120b-a12b:free | 0 | n/a | n/a | n/a | n/a | n/a | 3 |

Per run:

| task | trial | model | result | failed assertions | agent claimed success | false success | turns | tool calls | stop reason |
|---|---|---|---|---|---|---|---|---|---|
| dynamodb_add_gsi | 1 | nvidia/nemotron-3-super-120b-a12b:free | PASS | - | y | no | 6 | 5 | finished |
| iam_least_privilege | 1 | nvidia/nemotron-3-super-120b-a12b:free | FAIL | no_excess_permissions | y | **YES** | 10 | 9 | finished |
| s3_lifecycle_add_rule | 1 | nvidia/nemotron-3-super-120b-a12b:free | FAIL | rule_count_is_3, archive_logs_unchanged, expire_cache_unchanged | y | **YES** | 6 | 5 | finished |
| s3_logs_bucket | 1 | nvidia/nemotron-3-super-120b-a12b:free | AGENT_ERROR | bucket_exists, versioning_not_enabled, public_access_fully_blocked, lifecycle_expires_30_days | n (no_claim) | no | 2 | 1 | error: RuntimeError: empty response: {'id': 'gen-1792266680-CcYRaZdCB9FQn2oelY3E', 'choices': None, 'created': None, 'model': None, 'object': None, 'metadata': None, 'moderation': None, 'service_tier': None, 'system_fingerprint': None, 'usage': None, 'error': {'message': 'Upstream idle timeout exceeded', 'code': 504, 'metadata': {'error_type': 'timeout'}}} |
| s3_notification_add | 1 | nvidia/nemotron-3-super-120b-a12b:free | AGENT_ERROR | ingest_config_preserved, thumbnails_config_added, thumbnails_policy_allows_s3, incoming_upload_reaches_ingest_q | n (no_claim) | no | 13 | 12 | error: RateLimitError: Error code: 429 - {'error': {'message': 'Rate limit exceeded: free-models-per-day. Add 10 credits to unlock 1000 free model requests per day', 'code': 429, 'metadata': {'headers': {'X-RateLimit-Limit': '50', 'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': '1792281600000'}, 'limit_source': 'openrouter_free_tier_daily', 'remedy_hint': 'Wait for the daily reset (see X-RateLimit-Reset), or purchase credits to raise your free-model daily limit.', 'provider_name': None}}, 'user_id': 'user_3KpqH50y6siKQ5zIUUioVmyRUGA'} |
| s3_policy_add_statement | 1 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| sns_sqs_fanout | 1 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| dynamodb_add_gsi | 2 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| iam_least_privilege | 2 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| s3_lifecycle_add_rule | 2 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| s3_logs_bucket | 2 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| s3_notification_add | 2 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| s3_policy_add_statement | 2 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| sns_sqs_fanout | 2 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| dynamodb_add_gsi | 3 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| iam_least_privilege | 3 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| s3_lifecycle_add_rule | 3 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| s3_logs_bucket | 3 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| s3_notification_add | 3 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| s3_policy_add_statement | 3 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |
| sns_sqs_fanout | 3 | nvidia/nemotron-3-super-120b-a12b:free | NOT_RUN | - | n/a | n/a | - | - | - |

Failed assertions:

- `iam_least_privilege` #1 / `nvidia/nemotron-3-super-120b-a12b:free`: [FAIL] no_excess_permissions: expected only s3:GetObject on finance-001/reports/*, item writes on invoices, (+ standard logs); observed broader than needed: ['s3:GetObject on arn:aws:s3:::finance-001 [inline:LambdaS3DynamoPolicy]', 's3:ListBucket on arn:aws:s3:::finance-001 [inline:LambdaS3DynamoPolicy]', 's3:ListBucket on arn:aws:s3:::finance-001/reports/* [inline:LambdaS3DynamoPolicy]', 'dynamodb:DeleteItem on arn:aws:dynamodb:us-east-1:000000000000:table/invoices [inline:LambdaS3DynamoPolicy]']
- `s3_lifecycle_add_rule` #1 / `nvidia/nemotron-3-super-120b-a12b:free`: [FAIL] rule_count_is_3: expected 3 rules; observed 1 rule(s): ['DeleteTmpObjects']
- `s3_lifecycle_add_rule` #1 / `nvidia/nemotron-3-super-120b-a12b:free`: [FAIL] archive_logs_unchanged: expected rule {"Filter": {"Prefix": "logs/"}, "ID": "archive-logs", "Status": "Enabled", "Transitions": [{"Days": 90, "StorageClass": "GLACIER"}]}; observed rule archive-logs is gone; remaining IDs: ['DeleteTmpObjects']
- `s3_lifecycle_add_rule` #1 / `nvidia/nemotron-3-super-120b-a12b:free`: [FAIL] expire_cache_unchanged: expected rule {"Expiration": {"Days": 14}, "Filter": {"Prefix": "cache/"}, "ID": "expire-cache", "Status": "Enabled"}; observed rule expire-cache is gone; remaining IDs: ['DeleteTmpObjects']
- `s3_logs_bucket` #1 / `nvidia/nemotron-3-super-120b-a12b:free`: [FAIL] bucket_exists: expected bucket app-logs-001 exists; observed HeadBucket failed: 404
- `s3_logs_bucket` #1 / `nvidia/nemotron-3-super-120b-a12b:free`: [FAIL] versioning_not_enabled: expected versioning never set or Suspended; observed GetBucketVersioning failed: NoSuchBucket
- `s3_logs_bucket` #1 / `nvidia/nemotron-3-super-120b-a12b:free`: [FAIL] public_access_fully_blocked: expected all four PublicAccessBlock flags true; observed GetPublicAccessBlock failed: NoSuchBucket
- `s3_logs_bucket` #1 / `nvidia/nemotron-3-super-120b-a12b:free`: [FAIL] lifecycle_expires_30_days: expected a rule with Status=Enabled and Expiration.Days=30; observed GetBucketLifecycleConfiguration failed: NoSuchBucket
- `s3_notification_add` #1 / `nvidia/nemotron-3-super-120b-a12b:free`: [FAIL] ingest_config_preserved: expected config {'QueueArn': 'arn:aws:sqs:us-east-1:000000000000:ingest-q', 'Events': ['s3:ObjectCreated:*'], 'Filter': [('prefix', 'incoming/')]}; observed queue configs: [{'QueueArn': 'arn:aws:sqs:us-east-1:000000000000:thumbnails-q', 'Events': ['s3:ObjectCreated:*'], 'Filter': []}]
- `s3_notification_add` #1 / `nvidia/nemotron-3-super-120b-a12b:free`: [FAIL] thumbnails_config_added: expected config: thumbnails-q, all ObjectCreated events, filter exactly prefix=images/; observed queue configs: [{'QueueArn': 'arn:aws:sqs:us-east-1:000000000000:thumbnails-q', 'Events': ['s3:ObjectCreated:*'], 'Filter': []}]
- `s3_notification_add` #1 / `nvidia/nemotron-3-super-120b-a12b:free`: [FAIL] thumbnails_policy_allows_s3: expected thumbnails-q policy allows s3.amazonaws.com sqs:SendMessage from arn:aws:s3:::uploads-001; observed no policy
- `s3_notification_add` #1 / `nvidia/nemotron-3-super-120b-a12b:free`: [FAIL] incoming_upload_reaches_ingest_q: expected an ObjectCreated event for incoming/grader-0b3211ada3cd4849a74bd13b069f8048.csv on ingest-q; observed no event for incoming/grader-0b3211ada3cd4849a74bd13b069f8048.csv within 8s (1 other message(s) seen)
