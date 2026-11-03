// Load test of the four busiest paths: feed, search, free times, test payment.
// One virtual person = a phone that opens a screen, reads for about 2 seconds, and so on.
import { check, sleep } from "k6";
import http from "k6/http";
import { Counter, Trend } from "k6/metrics";

const BASE = __ENV.BASE_URL || "http://backend-load:8000/api/v1";
const VUS = Number(__ENV.VUS || 10);
const DURATION = __ENV.DURATION || "60s";
const THINK_SECONDS = 2;
const PAYMENT_POLLS = 30;

const data = JSON.parse(open("./data.json"));

const feed = new Trend("time_feed", true);
const search = new Trend("time_search", true);
const slots = new Trend("time_slots", true);
const pay = new Trend("time_pay_requests", true);
const held = new Trend("time_until_held", true);
const failures = new Counter("failed_requests");

export const options = {
  scenarios: {
    phones: { executor: "constant-vus", vus: VUS, duration: DURATION, gracefulStop: "30s" },
  },
  summaryTrendStats: ["med", "p(95)", "max"],
};

function timed(metric, name, response, expected = 200) {
  metric.add(response.timings.duration);
  if (!check(response, { [`${name} ${expected}`]: (r) => r.status === expected })) {
    failures.add(1);
    console.error(`${name}: HTTP ${response.status} after ${response.timings.duration} ms`);
  }
  return response;
}

function authed(token) {
  return {
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      "X-SG-Client": "web",
    },
  };
}

function payOnce(token) {
  const params = authed(token);
  const created = timed(
    pay,
    "create payment",
    http.post(
      `${BASE}/dev/payments`,
      JSON.stringify({
        seller_slug: data.seller_slug,
        items_minor: 10000,
        delivery_minor: 1000,
        description: "Load test",
      }),
      params,
    ),
    201,
  );
  if (created.status !== 201) return;
  const id = created.json("id");
  const started = Date.now();
  timed(
    pay,
    "test outcome",
    http.post(
      `${BASE}/payments/${id}/test-outcome`,
      JSON.stringify({ outcome: "succeeded" }),
      params,
    ),
  );
  // The money is held once the signed webhook went through the worker.
  for (let attempt = 0; attempt < PAYMENT_POLLS; attempt += 1) {
    sleep(1);
    const answer = timed(pay, "read payment", http.get(`${BASE}/payments/${id}`, params));
    if (answer.status === 200 && answer.json("status") === "held") {
      held.add(Date.now() - started);
      return;
    }
  }
  failures.add(1);
}

export default function () {
  const token = data.tokens[(__VU - 1) % data.tokens.length];
  const params = authed(token);

  timed(feed, "feed", http.get(`${BASE}/feed?city=Cotonou&country=BJ`, params));
  sleep(THINK_SECONDS);

  const word = data.words[__ITER % data.words.length];
  timed(search, "search", http.get(`${BASE}/pros?q=${encodeURIComponent(word)}`));
  sleep(THINK_SECONDS);

  timed(
    slots,
    "slots",
    http.get(`${BASE}/pros/${data.booking_slug}/booking/slots?service=${data.service_id}&days=7`),
  );
  sleep(THINK_SECONDS);

  // One round in five ends with a payment: most people look before they pay.
  if (__ITER % 5 === 0) payOnce(token);
  sleep(THINK_SECONDS);
}

export function handleSummary(summary) {
  const row = (name) => {
    const metric = summary.metrics[name];
    return metric
      ? {
          count: metric.values.count ?? null,
          median: metric.values.med,
          p95: metric.values["p(95)"],
          max: metric.values.max,
        }
      : null;
  };
  const report = {
    vus: VUS,
    duration: DURATION,
    requests: summary.metrics.http_reqs?.values.count ?? 0,
    per_second: summary.metrics.http_reqs?.values.rate ?? 0,
    failed: summary.metrics.failed_requests?.values.count ?? 0,
    feed: row("time_feed"),
    search: row("time_search"),
    slots: row("time_slots"),
    pay_requests: row("time_pay_requests"),
    until_held: row("time_until_held"),
  };
  return {
    [`results/vus-${VUS}.json`]: JSON.stringify(report, null, 2),
    stdout: `${JSON.stringify(report)}\n`,
  };
}
