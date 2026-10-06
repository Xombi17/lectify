#!/usr/bin/env bash
# Pause / resume the deployed Lectify stack to save credits, with live progress.
# Usage: aws-pause.sh pause|resume|status [--yes]
#   pause   scale web+worker ASGs to 0, then stop the RDS instance
#   resume  start RDS, scale ASGs back, wait until the ALB serves /healthz
#   status  show what is running (read-only)
# Not paused: the ALB (~$0.5-0.8/day) and RDS storage. AWS auto-restarts a stopped
# RDS after 7 days; re-run `pause` if you are away longer. `make deploy` also undoes a pause.
# Resources are discovered from the CloudFormation stacks (no hard-coded names).
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
export AWS_PROFILE="${AWS_PROFILE:-lectify}" AWS_REGION="${AWS_REGION:-ap-southeast-2}" AWS_DEFAULT_REGION="${AWS_REGION:-ap-southeast-2}"
STATE="${PAUSE_STATE:-cdk.out/pause-state.env}"   # cdk.out/ is gitignored
TIMEOUT="${PAUSE_TIMEOUT:-1200}"                  # seconds per wait
CMD="${1:-}"; YES=0; [ "${2:-}" = "--yes" ] && YES=1

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }

command -v aws >/dev/null || die "aws cli not found"
aws sts get-caller-identity >/dev/null 2>&1 || die "not logged in. Run: aws login --profile $AWS_PROFILE"

stack_res() { aws cloudformation describe-stack-resources --stack-name "$1" --query "StackResources[?ResourceType=='$2'].[LogicalResourceId,PhysicalResourceId]" --output text 2>/dev/null; }
WEB_ASG=$(stack_res ComputeStack AWS::AutoScaling::AutoScalingGroup | awk '/^WebAsg/{print $2}')
WORKER_ASG=$(stack_res ComputeStack AWS::AutoScaling::AutoScalingGroup | awk '/^WorkerAsg/{print $2}')
DB=$(stack_res DataStack AWS::RDS::DBInstance | awk 'NR==1{print $2}')
TGS=$(stack_res ComputeStack AWS::ElasticLoadBalancingV2::TargetGroup | awk '{print $2}')
ALB=$(aws cloudformation describe-stacks --stack-name ComputeStack --query "Stacks[0].Outputs[?OutputKey=='AlbDnsName'].OutputValue" --output text 2>/dev/null)
[ -n "$WEB_ASG" ] && [ -n "$WORKER_ASG" ] && [ -n "$DB" ] || die "could not find ComputeStack/DataStack resources (is the stack deployed?)"

asg_field() { aws autoscaling describe-auto-scaling-groups --auto-scaling-group-names "$1" --query "AutoScalingGroups[0].$2" --output text; }
asg_sizes() { asg_field "$1" '[MinSize,MaxSize,DesiredCapacity]' | tr '\t' '/'; }
inst_count() { aws ec2 describe-instances --filters "Name=tag:aws:autoscaling:groupName,Values=$1" "Name=instance-state-name,Values=pending,running,shutting-down,stopping" --query 'length(Reservations[].Instances[])' --output text; }
inst_running() { aws ec2 describe-instances --filters "Name=tag:aws:autoscaling:groupName,Values=$1" "Name=instance-state-name,Values=running" --query 'length(Reservations[].Instances[])' --output text; }
db_status() { aws rds describe-db-instances --db-instance-identifier "$DB" --query 'DBInstances[0].DBInstanceStatus' --output text; }
healthy_targets() { local n=0 t; for t in $TGS; do n=$((n + $(aws elbv2 describe-target-health --target-group-arn "$t" --query "length(TargetHealthDescriptions[?TargetHealth.State=='healthy'])" --output text))); done; echo "$n"; }
http_code() { curl -s -o /dev/null -w '%{http_code}' --max-time 8 "http://$ALB$1" 2>/dev/null || echo 000; }

# wait_for "<label>" "<command printing current value>" "<target regex>"; prints a line on every change + a heartbeat.
wait_for() {
  local label="$1" cmd="$2" want="$3" start=$SECONDS last="" cur beat=0
  while :; do
    cur=$(eval "$cmd" 2>/dev/null)
    [[ "$cur" =~ $want ]] && { log "  done: $label = $cur ($((SECONDS - start))s)"; return 0; }
    if [ "$cur" != "$last" ] || [ $((SECONDS - beat)) -ge 30 ]; then log "  waiting: $label = ${cur:-?} ($((SECONDS - start))s)"; last="$cur"; beat=$SECONDS; fi
    [ $((SECONDS - start)) -ge "$TIMEOUT" ] && { log "  TIMEOUT waiting for $label (last: $cur)"; return 1; }
    sleep 10
  done
}

show_status() {
  log "ASG web    $WEB_ASG   min/max/desired=$(asg_sizes "$WEB_ASG")   running=$(inst_running "$WEB_ASG")"
  log "ASG worker $WORKER_ASG   min/max/desired=$(asg_sizes "$WORKER_ASG")   running=$(inst_running "$WORKER_ASG")"
  log "RDS        $DB   status=$(db_status)"
  log "ALB        $ALB   /healthz=$(http_code /healthz)  healthy targets=$(healthy_targets)"
  [ -f "$STATE" ] && log "saved sizes for resume: $(tr '\n' ' ' < "$STATE")"
  return 0
}

confirm() { [ "$YES" = 1 ] && return 0; read -r -p "$1 [y/N] " a; [[ "$a" =~ ^[Yy]$ ]]; }

pause() {
  log "== PAUSE =="; show_status; confirm "Scale servers to 0 and stop the database?" || die "aborted"
  # Remember sizes (only if currently up) so resume restores them exactly.
  if [ "$(asg_field "$WEB_ASG" DesiredCapacity)" != "0" ] || [ "$(asg_field "$WORKER_ASG" DesiredCapacity)" != "0" ]; then
    mkdir -p "$(dirname "$STATE")"
    { echo "WEB_MIN=$(asg_field "$WEB_ASG" MinSize)"; echo "WEB_DESIRED=$(asg_field "$WEB_ASG" DesiredCapacity)"
      echo "WORKER_MIN=$(asg_field "$WORKER_ASG" MinSize)"; echo "WORKER_DESIRED=$(asg_field "$WORKER_ASG" DesiredCapacity)"; } > "$STATE"
    log "saved sizes to $STATE"
  fi
  log "1/3 scaling ASGs to 0"
  aws autoscaling update-auto-scaling-group --auto-scaling-group-name "$WEB_ASG" --min-size 0 --desired-capacity 0 || die "web ASG update failed"
  aws autoscaling update-auto-scaling-group --auto-scaling-group-name "$WORKER_ASG" --min-size 0 --desired-capacity 0 || die "worker ASG update failed"
  wait_for "web instances" "inst_count $WEB_ASG" '^0$' || exit 1
  wait_for "worker instances" "inst_count $WORKER_ASG" '^0$' || exit 1
  log "2/3 stopping RDS"
  case "$(db_status)" in
    available) aws rds stop-db-instance --db-instance-identifier "$DB" --query 'DBInstance.DBInstanceStatus' --output text >/dev/null || die "stop-db-instance failed" ;;
    stopped|stopping) log "  RDS already $(db_status)" ;;
    *) die "RDS is '$(db_status)', cannot stop now. Retry in a few minutes" ;;
  esac
  wait_for "RDS" db_status '^stopped$' || exit 1
  log "3/3 verifying"; show_status
  log "PAUSED. Still billing: ALB + RDS storage. Resume with: $0 resume"
}

resume() {
  log "== RESUME =="; show_status
  [ -f "$STATE" ] && . "$STATE"
  : "${WEB_MIN:=1}" "${WEB_DESIRED:=1}" "${WORKER_MIN:=1}" "${WORKER_DESIRED:=1}"
  log "1/4 starting RDS"
  case "$(db_status)" in
    stopped) aws rds start-db-instance --db-instance-identifier "$DB" --query 'DBInstance.DBInstanceStatus' --output text >/dev/null || die "start-db-instance failed" ;;
    available|starting) log "  RDS already $(db_status)" ;;
    *) log "  RDS is '$(db_status)', waiting for it to settle" ;;
  esac
  wait_for "RDS" db_status '^available$' || exit 1
  log "2/4 scaling ASGs (web min=$WEB_MIN desired=$WEB_DESIRED, worker min=$WORKER_MIN desired=$WORKER_DESIRED)"
  aws autoscaling update-auto-scaling-group --auto-scaling-group-name "$WEB_ASG" --min-size "$WEB_MIN" --desired-capacity "$WEB_DESIRED" || die "web ASG update failed"
  aws autoscaling update-auto-scaling-group --auto-scaling-group-name "$WORKER_ASG" --min-size "$WORKER_MIN" --desired-capacity "$WORKER_DESIRED" || die "worker ASG update failed"
  log "3/4 waiting for instances (boot + bootstrap takes ~3-5 min)"
  wait_for "web instances running" "inst_running $WEB_ASG" "^$WEB_DESIRED$" || exit 1
  wait_for "worker instances running" "inst_running $WORKER_ASG" "^$WORKER_DESIRED$" || exit 1
  log "4/4 waiting for the load balancer to serve traffic"
  wait_for "healthy targets" healthy_targets '^[2-9]$' || exit 1
  wait_for "GET /healthz" "http_code /healthz" '^200$' || exit 1
  wait_for "GET /api/auth/me (expects 401 = API up)" "http_code /api/auth/me" '^401$' || exit 1
  show_status; log "RESUMED: http://$ALB"
}

case "$CMD" in
  pause) pause ;;
  resume) resume ;;
  status) show_status ;;
  *) sed -n '2,9p' "$0"; exit 1 ;;
esac
