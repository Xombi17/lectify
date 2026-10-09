#!/usr/bin/env bash
# Provider-stubbed worker scale-out / scale-in demo (VER-03).
# Usage: scale-demo.sh stub-on [--delay S]
#        scale-demo.sh stub-off
#        scale-demo.sh run [--count N] [--scale-out-timeout MIN] [--scale-in-timeout MIN]
#   stub-on   set SSM /lectify/STUB_PROVIDERS=1 + /lectify/STUB_DELAY_S (default 60), restart workers
#   stub-off  delete both SSM params, restart workers
#   run       upload N tiny lectures as the demo teacher (default 30), poll backlog + worker ASG every
#             30s, require scale-out (InService > 1) then scale-in (Desired back to 1). Refuses to run
#             unless /lectify/STUB_PROVIDERS is "1" (no paid provider calls).
# Env: AWS_PROFILE (lectify) AWS_REGION (ap-southeast-2) TEACHER_EMAIL (teacher@demo.lectify)
#      TEACHER_PASSWORD (else silent prompt) AUDIO_FILE (else 5s sine wav via ffmpeg)
# Expect ~30-45 min wall clock (2 min alarm + ~5 min EC2 boot/warmup + 15 min scale-in window).
# DeadLetterJobs / 5xx alarms should stay quiet; any email during the demo is a real finding.
# All output is also written to cdk.out/scale-demo-<UTC timestamp>.log (gitignored).
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
case "${1:-}" in ""|-h|--help|help) sed -n '2,15p' "$0"; exit 0;; esac
export AWS_PROFILE="${AWS_PROFILE:-lectify}" AWS_REGION="${AWS_REGION:-ap-southeast-2}" AWS_DEFAULT_REGION="${AWS_REGION:-ap-southeast-2}"
mkdir -p cdk.out
LOG="cdk.out/scale-demo-$(date -u +%Y%m%dT%H%M%SZ).log"
exec > >(tee -a "$LOG") 2>&1

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }
for c in aws curl jq; do command -v "$c" >/dev/null || die "$c not found on PATH"; done
aws sts get-caller-identity >/dev/null 2>&1 || die "not logged in. Run: aws login --profile $AWS_PROFILE"

stack_res() { aws cloudformation describe-stack-resources --stack-name "$1" --query "StackResources[?ResourceType=='$2'].[LogicalResourceId,PhysicalResourceId]" --output text 2>/dev/null; }
stack_out() { aws cloudformation describe-stacks --stack-name "$1" --query "Stacks[0].Outputs[?OutputKey=='$2'].OutputValue" --output text 2>/dev/null; }
WORKER_ASG=$(stack_res ComputeStack AWS::AutoScaling::AutoScalingGroup | awk '/^WorkerAsg/{print $2}')
ALB=$(stack_out ComputeStack AlbDnsName)
TQ=$(stack_out DataStack TranscribeQueueUrl)
MQ=$(stack_out DataStack MaterialsQueueUrl)
[ -n "$WORKER_ASG" ] && [ -n "$ALB" ] && [ -n "$TQ" ] && [ -n "$MQ" ] || die "could not discover ComputeStack/DataStack resources (is the stack deployed?)"

asg_q() { aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "$WORKER_ASG" --query "$1" --output text; }

restart_workers() {
  local ids cmd_id
  ids=$(aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "$WORKER_ASG" --query "AutoScalingGroups[0].Instances[?LifecycleState=='InService'].InstanceId" --output text)
  [ -n "$ids" ] || { log "no InService workers; new instances read SSM at boot"; return 0; }
  # shellcheck disable=SC2086
  cmd_id=$(aws ssm send-command --document-name AWS-RunShellScript --instance-ids $ids \
    --parameters 'commands=["systemctl restart lectify-worker"]' --query Command.CommandId --output text) || die "send-command failed"
  log "restarting workers ($ids), command $cmd_id"
  sleep 5
  local i
  for i in $ids; do
    aws ssm wait command-executed --command-id "$cmd_id" --instance-id "$i" || die "restart failed on $i"
  done
  log "workers restarted"
}

stub_on() {
  local delay=60
  [ "${1:-}" = "--delay" ] && delay="${2:?--delay needs seconds}"
  aws ssm put-parameter --name /lectify/STUB_PROVIDERS --value 1 --type String --overwrite >/dev/null || die "put STUB_PROVIDERS failed"
  aws ssm put-parameter --name /lectify/STUB_DELAY_S --value "$delay" --type String --overwrite >/dev/null || die "put STUB_DELAY_S failed"
  log "stub ON (delay ${delay}s)"; restart_workers
}

stub_off() {
  aws ssm delete-parameters --names /lectify/STUB_PROVIDERS /lectify/STUB_DELAY_S >/dev/null || die "delete-parameters failed"
  log "stub OFF"; restart_workers
}

backlog() {
  local t=0 q n
  for q in "$TQ" "$MQ"; do
    n=$(aws sqs get-queue-attributes --queue-url "$q" --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible \
      --query 'Attributes.[ApproximateNumberOfMessages,ApproximateNumberOfMessagesNotVisible]' --output text | awk '{print $1+$2}')
    t=$((t + ${n:-0}))
  done
  echo "$t"
}

http() { # http <expected-2xx-label> curl args...; sets BODY, dies on non-2xx
  local label="$1"; shift
  local out code
  out=$(curl -s -w '\n%{http_code}' --max-time 60 "$@") || die "$label: curl failed"
  code=${out##*$'\n'}; BODY=${out%$'\n'*}
  [[ "$code" =~ ^2 ]] || die "$label: HTTP $code"
}

run() {
  local count=30 out_to=20 in_to=40
  while [ $# -gt 0 ]; do
    case "$1" in
      --count) count="$2"; shift 2;; --scale-out-timeout) out_to="$2"; shift 2;;
      --scale-in-timeout) in_to="$2"; shift 2;; *) die "unknown option $1";;
    esac
  done
  [ "$(aws ssm get-parameter --name /lectify/STUB_PROVIDERS --query Parameter.Value --output text 2>/dev/null)" = "1" ] \
    || die "stub providers are off (would spend real provider quota). Run: $0 stub-on"

  local email="${TEACHER_EMAIL:-teacher@demo.lectify}" pw="${TEACHER_PASSWORD:-}"
  [ -n "$pw" ] || { read -r -s -p "Password for $email: " pw; echo; }
  local tmp; tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
  local audio="${AUDIO_FILE:-}"
  if [ -z "$audio" ]; then
    command -v ffmpeg >/dev/null || die "set AUDIO_FILE or install ffmpeg"
    audio="$tmp/demo.wav"
    ffmpeg -loglevel error -f lavfi -i sine=frequency=440:duration=5 -ac 1 "$audio" || die "ffmpeg failed"
  fi
  local size; size=$(stat -c %s "$audio")

  http login -X POST "http://$ALB/api/auth/login" -H 'Content-Type: application/json' \
    -d "$(jq -n --arg e "$email" --arg p "$pw" '{email:$e,password:$p}')"
  local token; token=$(jq -r .access_token <<<"$BODY"); pw=""
  [ -n "$token" ] && [ "$token" != null ] || die "login returned no token"
  http assignments "http://$ALB/api/enrollment/teacher-assignments/mine" -H "Authorization: Bearer $token"
  local class_id; class_id=$(jq -r '.[0].class_id // empty' <<<"$BODY")
  [ -n "$class_id" ] || die "teacher has no assigned class: run make seed-demo first"

  log "uploading $count lectures"
  local i lid url args
  for ((i = 1; i <= count; i++)); do
    http "upload-url $i" -X POST "http://$ALB/api/lectures/upload-url" -H "Authorization: Bearer $token" -H 'Content-Type: application/json' \
      -d "$(jq -n --arg t "scale-demo $i" --arg c "$class_id" --argjson s "$size" '{title:$t,class_id:$c,filename:"demo.wav",content_type:"audio/wav",size:$s}')"
    lid=$(jq -r .lecture_id <<<"$BODY"); url=$(jq -r .url <<<"$BODY")
    args=(); while IFS= read -r kv; do args+=(-F "$kv"); done < <(jq -r '.fields | to_entries[] | "\(.key)=\(.value)"' <<<"$BODY")
    http "s3 upload $i" -X POST "$url" "${args[@]}" -F "file=@$audio"
    http "upload-complete $i" -X POST "http://$ALB/api/lectures/$lid/upload-complete" -H "Authorization: Bearer $token"
  done
  log "backlog created"

  local start=$SECONDS prev="" des ins bl phase=A
  while :; do
    des=$(asg_q 'AutoScalingGroups[0].DesiredCapacity'); ins=$(asg_q "length(AutoScalingGroups[0].Instances[?LifecycleState=='InService'])"); bl=$(backlog)
    log "phase=$phase backlog=$bl desired=$des inservice=$ins"
    [ "$prev" != "" ] && [ "$prev" != "$des/$ins" ] && log "TRANSITION desired/inservice $prev -> $des/$ins"
    prev="$des/$ins"
    if [ "$phase" = A ]; then
      [ "${ins:-0}" -gt 1 ] && { log "SCALE-OUT observed after $((SECONDS - start))s"; phase=B; start=$SECONDS; continue; }
      [ $((SECONDS - start)) -ge $((out_to * 60)) ] && die "scale-out not observed within ${out_to} min"
    else
      [ "${des:-2}" -le 1 ] && { log "SCALE-IN observed after $((SECONDS - start))s"; break; }
      [ $((SECONDS - start)) -ge $((in_to * 60)) ] && die "scale-in not observed within ${in_to} min"
    fi
    sleep 30
  done

  log "last 10 scaling activities"
  aws autoscaling describe-scaling-activities --auto-scaling-group-name "$WORKER_ASG" --max-items 10 \
    --query 'Activities[].[StartTime,Description,StatusCode]' --output text
  log "done. Now run: $0 stub-off"
}

case "$1" in
  stub-on) shift; stub_on "$@";;
  stub-off) stub_off;;
  run) shift; run "$@";;
  *) die "unknown subcommand '$1' (stub-on | stub-off | run)";;
esac
log "log: $LOG"
