// Steady-state authenticated browse load (VER-04). Uses pre-minted tokens only.
// Mint: python -m scripts.load_users mint --count 200   (see backend/scripts/load_users.py)
// Run from the operator laptop against your OWN stack, never from a stack instance:
//   k6 run -e BASE_URL=http://<AlbDnsName> loadtest/browse.js --summary-export loadtest/out/browse-summary.json
// Optional: -e TOKENS=./out/tokens.json  -e STAGES="30s:50,2m:50,30s:100,2m:100"
import http from "k6/http";
import { check, sleep } from "k6";
import { SharedArray } from "k6/data";

const BASE = __ENV.BASE_URL;
if (!BASE) throw new Error("BASE_URL is required");

const tokens = new SharedArray("tokens", () =>
  JSON.parse(open(__ENV.TOKENS || "./out/tokens.json")),
);

const DEFAULT_STAGES = [50, 100, 250, 500, 1000, 2000]
  .map((n) => `30s:${n},2m:${n}`)
  .join(",");

function parseStages(s) {
  return s.split(",").map((p) => {
    const [duration, target] = p.split(":");
    return { duration, target: Number(target) };
  });
}

export const options = {
  scenarios: {
    browse: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: parseStages(__ENV.STAGES || DEFAULT_STAGES),
      gracefulRampDown: "30s",
    },
  },
  thresholds: {
    http_req_failed: [{ threshold: "rate<0.01", abortOnFail: false }],
    http_req_duration: [{ threshold: "p(95)<1000", abortOnFail: false }],
  },
};

const WORDS = ["lecture", "algorithm", "database", "network", "memory", "function"];

export default function () {
  const t = tokens[(__VU - 1) % tokens.length].token;
  const headers = { Authorization: `Bearer ${t}` };
  const ok = (r) => check(r, { "status 200": (x) => x.status === 200 });

  ok(http.get(`${BASE}/api/auth/me`, { headers, tags: { name: "me" } }));

  const pub = http.get(`${BASE}/api/lectures/published`, { headers, tags: { name: "published" } });
  ok(pub);
  let list = [];
  try {
    list = pub.json();
  } catch (e) {
    list = [];
  }
  if (Array.isArray(list) && list.length > 0) {
    const item = list[Math.floor(Math.random() * list.length)];
    ok(http.get(`${BASE}/api/lectures/${item.id}`, { headers, tags: { name: "detail" } }));
  }

  const q = WORDS[Math.floor(Math.random() * WORDS.length)];
  ok(http.get(`${BASE}/api/search?q=${q}`, { headers, tags: { name: "search" } }));

  sleep(1 + Math.random() * 2);
}
