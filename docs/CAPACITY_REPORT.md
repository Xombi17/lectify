# Lectify Capacity Report

Every number here comes from a real run on 2026-10-09 (k6 summary exports and CloudWatch); nothing is extrapolated. No hostnames, IPs or account ids are included.

## 1. Summary

Measured sustainable concurrent users: 20 vs ~2,000 target.

Verdict: Not met. The stack sustains about 1% of the target (roughly 100x short). At 20 users the load balancer p95 was 0.73 s with zero errors; at 25 users it was already 2.34 s, and it reached about 30 s at 400 users with throughput flat at about 23 req/s. The first limit is the API database connection pool (7 connections), not CPU.

## 2. Definition of "concurrent user"

One k6 VU running the browse loop (`/api/auth/me`, `/api/lectures/published`, lecture detail, `/api/search`) with 1-3 s think time. Sustainable = p95 < 1 s and error rate < 1%. Because k6 summary exports give whole-run totals only, the per-stage p95 is taken from the ALB `TargetResponseTime` p95 per minute, time-aligned to each k6 stage (see section 5).

## 3. System under test

| Item | Value |
|---|---|
| Web/API instance type | t3.small (API and web on the same instance) |
| Web ASG min / max / actual at test time | 1 / 2 / 1 (no scaling policy on the web tier) |
| Worker ASG min / max / actual at test time | 1 / 3 / 1 (idle during the tests) |
| RDS class | db.t4g.micro, PostgreSQL 16 |
| DB_POOL_SIZE / DB_MAX_OVERFLOW | 5 / 2 (code defaults; max 7 connections per API process) |
| RDS max_connections (`SHOW max_connections`) | not captured; RDS parameter is `LEAST({DBInstanceClassMemory/9531392},5000)` |
| Region | ap-southeast-2 |
| Date | 2026-10-09 |

## 4. Method

- Tokens: pre-minted with `python -m scripts.load_users mint` for 200 seeded load users (no login in steady state).
- Load generator location: operator laptop outside AWS, over the public internet (about 0.4 s network round trip; the minimum client-side request time was 377 ms against 0.02 s at the ALB).
- k6 version: v2.3.0
- Stages: run A (find the break): 30 s ramp + 1 min hold at 25, 50, 100, 200, 400 VUs, 12:02:18-12:10:18 UTC. Run B (find the limit): same shape at 5, 10, 15, 20 VUs, about 12:17:29-12:23:34 UTC. Both runs were hand-started with a reduced stage list, not the script's default ramp to 2,000.

## 5. Steady-state results

k6 whole-run totals (p99 is not in the k6 summary export: not captured):

| Run | Max VUs | req/s | p50 | p95 | p99 | error % |
|---|---|---|---|---|---|---|
| A | 400 | 21.1 | 3.95 s | 21.05 s | not captured | 0.01 |
| B | 20 | 10.4 | 537 ms | 1.05 s (client side, includes ~0.4 s network RTT) | not captured | 0.00 |

Per stage, from the ALB (server side), time-aligned to the k6 stages:

| Stage VUs | ALB requests/min | ALB p95 | 5xx |
|---|---|---|---|
| 5 | 316 | 0.44 s | 0 |
| 10 | 843 | 0.35 s | 0 |
| 15 | 803 | 0.59 s | 0 |
| 20 | 989 | 0.73 s | 0 |
| 25 | 948 | 2.34 s | 0 |
| 50 | 1,311-1,382 | 2.70-4.77 s | 0 |
| 100 | 1,377 | 6.67 s | 0 |
| 200 | 1,405-1,639 | 13.4-15.5 s | 0 |
| 400 | 1,301 | 29.7 s | 0 |

Minutes overlap stage boundaries, so values are approximate within a stage. Highest stage that held p95 < 1 s with 0 errors: 20 users.

CloudWatch (browse runs): ALB RequestCount peak 1,639 per minute; web instance CPU max 11.1% (5-minute buckets; no CPU-credit throttling, 0 surplus credits); RDS CPU max 7.8%; RDS DatabaseConnections max 7.

## 6. Login storm

Reported separately (bcrypt-bound). Constant 5 logins/s for 2 min, about 12:11:34-12:13:58 UTC, started about 75 s after run A ended (shorter gap than planned, so some run A queue may overlap its first minute).

| Rate | p95 | errors | API CPU |
|---|---|---|---|
| 5/s target (3.86/s achieved, 45 iterations dropped) | 31.7 s (p50 17.5 s, max 33.2 s) | 10.61% (59 of 556); ALB logged 56 target 5xx | 50.4% max (5-minute bucket covering the storm) |

## 7. First bottleneck and evidence

The API database connection pool. RDS DatabaseConnections peaked at exactly 7, which equals DB_POOL_SIZE 5 + DB_MAX_OVERFLOW 2, while the web instance CPU peaked at 11.1% and RDS CPU at 7.8%. Throughput stopped growing at about 23 req/s from the 50-user stage while ALB p95 kept rising from 2.7 s to 29.7 s, and maximum client latencies were 56 s (browse) and 33 s (login). That pattern is requests queueing for a connection, not a CPU limit. The evidence is correlational: no application-level pool metric was captured, and the uvicorn worker count and pool timeout were not verified in this phase. The login storm adds CPU pressure (50.4%) on top of the same limit.

## 8. Scale-out demo evidence

VER-03, run on 2026-10-09 (ap-southeast-2) with `STUB_PROVIDERS=1`: transcription replaced by a sleep of `STUB_DELAY_S=60` s per job, no provider calls. `scale-demo.sh run` uploaded 30 five-second WAV lectures through the real presigned-upload flow (the pipeline-backlog gauge read 31 after upload). Times are local (UTC+5:30).

| Time | Event | Backlog | Desired | InService |
|---|---|---|---|---|
| 15:48 | Backlog created | 31 | 1 | 1 |
| 15:49:20 | Scale-out alarm fired, desired 1 -> 3 | 31 | 3 | 1 |
| 15:49:59 | Both new workers in service (script: SCALE-OUT observed) | 31 | 3 | 3 |
| 15:55 | Draining on 3 workers | 27 | 3 | 3 |
| ~16:27 | Backlog at resting level | 1 | 3 | 3 |
| 16:44:57 | Scale-in alarm fired (backlog <= 1 for 15 consecutive minutes) | 1 | 3 | 3 |
| 16:45:00 | Desired 3 -> 2, instance i-<redacted> terminated | 1 | 2 | 2 |
| 16:46:05 | Desired 2 -> 1, instance i-<redacted> terminated | 1 | 1 | 1 |

- **Time to scale-out:** about 2 min (129 s from the script's first poll to 3 workers in service).
- **Time to scale-in:** about 19 min after the backlog reached its resting level (~16:27 to 16:46:05), which is the 15-minute alarm window plus stepwise termination. Full drain of the 31 jobs on 3 workers took about 35 min.
- **Scaling activities (all Successful):** "Launching a new EC2 instance: i-<redacted>" x2 (alarm: WorkerScaleOut, 1 -> 3); "Terminating EC2 instance: i-<redacted>" (alarm: WorkerScaleIn, 3 -> 2); "Terminating EC2 instance: i-<redacted>" (alarm: WorkerScaleIn, 2 -> 1).
- **Caveat:** the script's 40-minute scale-in timeout started at scale-out (15:49:59) and expired at 16:30:33, only ~3 min after the backlog finished draining, so the script exited non-zero ("scale-in not observed"). The scale-in above was observed afterwards from the ASG scaling activities and the alarm's state history, not by the script. Drain plus the 15-minute alarm window needs a budget of about 60 min or more.
- **Cleanup:** `stub-off` ran at 16:32 and `/lectify/STUB_PROVIDERS` no longer exists.

## 9. Findings

- No login rate limiting (noted, not fixed).
- Web ASG has no CPU scaling policy.
- Per-request token blacklist DB lookup adds one query per authenticated request.
- The API connection pool (7 connections) is the first limit while CPU and RDS stay nearly idle; the RDS parameter formula implies far more connections than the API can use.
- Running instances do not pick up new backend code after `make deploy` (the backend zip is fetched once at boot); `load_users.py` had to be copied onto the instance by hand for seeding.
- The scale-demo scale-in timeout (40 min) is too short for drain plus the 15-minute alarm window.

## 10. Not claimed

No capacity is claimed beyond the measured numbers above. Measured: 20 concurrent browse users held p95 < 1 s; 25 did not. Nothing is claimed for other mixes, longer durations, or multiple API instances (the web tier never scaled beyond one instance). To approach 2,000 users, the likely work, listed as findings only and not implemented in this phase, is a larger or tunable DB pool and more API workers per instance, a CPU or latency scaling policy on the web ASG, and a re-test to find the next bottleneck.
