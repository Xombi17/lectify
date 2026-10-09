// Login storm (VER-04), reported SEPARATELY from steady-state browse.
// bcrypt-bound: expect an API CPU spike and possibly an Api5xx alarm email.
// Run from the operator laptop against your OWN stack, never from a stack instance:
//   k6 run -e BASE_URL=http://<AlbDnsName> -e LOAD_USER_PASSWORD=... loadtest/login_storm.js --summary-export loadtest/out/login-summary.json
// Optional: -e RATE=5 -e DURATION=2m -e USERS=200
import http from "k6/http";
import { check } from "k6";

const BASE = __ENV.BASE_URL;
if (!BASE) throw new Error("BASE_URL is required");
const PASSWORD = __ENV.LOAD_USER_PASSWORD;
if (!PASSWORD) throw new Error("LOAD_USER_PASSWORD is required");
const USERS = Number(__ENV.USERS || 200);

export const options = {
  scenarios: {
    login_storm: {
      executor: "constant-arrival-rate",
      rate: Number(__ENV.RATE || 5),
      timeUnit: "1s",
      duration: __ENV.DURATION || "2m",
      preAllocatedVUs: 50,
      maxVUs: 200,
    },
  },
  thresholds: {
    http_req_failed: [{ threshold: "rate<0.01", abortOnFail: false }],
    http_req_duration: [{ threshold: "p(95)<1000", abortOnFail: false }],
  },
};

export default function () {
  const n = String(__ITER % USERS).padStart(4, "0");
  const res = http.post(
    `${BASE}/api/auth/login`,
    JSON.stringify({ email: `load${n}@demo.lectify`, password: PASSWORD }),
    { headers: { "Content-Type": "application/json" }, tags: { name: "login" } },
  );
  check(res, { "status 200": (r) => r.status === 200 });
}
