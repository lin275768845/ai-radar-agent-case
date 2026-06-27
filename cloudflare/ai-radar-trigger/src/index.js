const DEFAULT_GITHUB_REF = "main";

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function sanitizeGitHubBody(body) {
  return String(body || "")
    .replace(/Bearer\s+[A-Za-z0-9._-]+/g, "Bearer ***")
    .replace(/github_pat_[A-Za-z0-9_]+/g, "github_pat_***")
    .replace(/gh[opsu]_[A-Za-z0-9_]+/g, "gh*_***");
}

function isTrueLike(value) {
  return ["true", "1", "yes", "on"].includes(
    String(value || "")
      .trim()
      .toLowerCase()
  );
}

async function dispatchGitHub(env, source) {
  const owner = env.GITHUB_OWNER || "lin275768845";
  const repo = env.GITHUB_REPO || "ai-radar-agent";
  const workflow = env.GITHUB_WORKFLOW || "daily.yml";
  const ref = env.GITHUB_REF || DEFAULT_GITHUB_REF;

  if (!env.GITHUB_TOKEN) {
    throw new Error("missing GITHUB_TOKEN");
  }

  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`;
  const payload = {
    ref,
    inputs: {
      date: "",
      dry_run: "false",
      skip_llm: "false",
      send_bot: "true",
      output_mode: "feishu_docx_import",
      tavily_enabled: "false",
      bocha_enabled: isTrueLike(env.BOCHA_ENABLED) ? "true" : "false",
      force_republish: "false",
      report_lint_policy: "warn",
      bot_block_on_lint_critical: "false"
    }
  };

  for (let attempt = 1; attempt <= 3; attempt++) {
    console.log(
      `GitHub dispatch attempt ${attempt} from ${source}: repo=${owner}/${repo}, workflow=${workflow}, ref=${ref}`
    );

    const resp = await fetch(url, {
      method: "POST",
      headers: {
        Accept: "application/vnd.github+json",
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "cloudflare-ai-radar-dispatcher"
      },
      body: JSON.stringify(payload)
    });

    const body = sanitizeGitHubBody(await resp.text()).slice(0, 500);
    console.log(
      `GitHub dispatch response attempt ${attempt} from ${source}: status=${resp.status}, body=${body}`
    );

    if (resp.ok) {
      console.log(`GitHub dispatch OK from ${source}: ${resp.status}`);
      return { ok: true, status: resp.status };
    }

    if (![429, 500, 502, 503, 504].includes(resp.status) || attempt === 3) {
      throw new Error(`GitHub dispatch failed: status=${resp.status}`);
    }

    await sleep(attempt * 3000);
  }

  throw new Error("GitHub dispatch failed after retries");
}

function runDispatchInBackground(env, ctx, source) {
  ctx.waitUntil(
    dispatchGitHub(env, source).catch((err) => {
      console.log(
        `GitHub dispatch final failure from ${source}: ${err && err.stack ? err.stack : err}`
      );
    })
  );
}

function hasValidManualAuth(request, env) {
  const header = request.headers.get("Authorization") || "";
  return Boolean(
    env.MANUAL_TRIGGER_SECRET &&
      header === `Bearer ${env.MANUAL_TRIGGER_SECRET}`
  );
}

export default {
  async scheduled(controller, env, ctx) {
    console.log(
      `scheduled fired: cron=${controller.cron}, ref=${env.GITHUB_REF || DEFAULT_GITHUB_REF}`
    );
    runDispatchInBackground(env, ctx, `cron:${controller.cron}`);
  },

  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    if (url.pathname !== "/trigger") {
      return new Response("AI Radar dispatcher is running.", {
        status: 200,
        headers: { "Content-Type": "text/plain; charset=utf-8" }
      });
    }

    if (!hasValidManualAuth(request, env)) {
      return new Response("Unauthorized", {
        status: 401,
        headers: { "Content-Type": "text/plain; charset=utf-8" }
      });
    }

    runDispatchInBackground(env, ctx, "manual");

    return Response.json(
      {
        ok: true,
        message: "GitHub workflow dispatch started in background",
        ref: env.GITHUB_REF || DEFAULT_GITHUB_REF
      },
      { status: 202 }
    );
  }
};
