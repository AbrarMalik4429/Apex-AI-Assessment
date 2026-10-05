# Part 9 — Model / Cost Comparison

Pricing checked on **6 October 2026**. Estimates are in USD and cover model API usage only. They are planning calculations, not measured production bills or latency benchmarks.

## Models compared

The local configuration selects **`openai/gpt-oss-120b` on Groq**. The fallback in [config.py](../app/config.py) is the 20B model, but this comparison uses the explicitly configured 120B model requested for the assessment. GPT-OSS is an OpenAI open-weight model served here by Groq; Groq is the inference provider, not the model author.

Claude is a reasonable comparison because this is a cross-provider selection decision. Haiku is used here for the app's short structured tasks; choosing a more expensive Claude tier would require evidence of better results on those tasks.

The alternative is **`claude-haiku-4-5-20251001` through the Anthropic API**, chosen as a focused-task comparison for intent extraction and evidence selection, not as a claim that it is the most capable Claude model.

| Attribute | GPT-OSS 120B on Groq | Claude Haiku 4.5 on Anthropic |
|---|---|---|
| Standard input price / 1M tokens | $0.15 | $1.00 |
| Standard output price / 1M tokens | $0.60 | $5.00 |
| Listed cached-input price / 1M tokens | $0.075 | $0.10 cache reads; cache writes have separate charges |
| Model size | 120B total parameters; mixture-of-experts with 5.1B active per forward pass | Parameter count not published in the cited model page; do not infer a size comparison. |
| Context capacity | 131,072 tokens | 200,000 tokens |
| Relevant capability | Reasoning and JSON-schema output | Candidate for classification/extraction; validate the schema-output integration before migration |
| Published speed information | Approximately 500 output tokens/second, as advertised by Groq | Positioned as the fastest Claude option; no comparable fixed tokens/second figure supplied on the cited model page. |

Sources: [Groq GPT-OSS 120B model/pricing](https://console.groq.com/docs/model/openai/gpt-oss-120b), [Anthropic Haiku 4.5 specifications](https://platform.claude.com/docs/en/models/haiku-4-5/overview) and [Anthropic standard pricing](https://platform.claude.com/docs/en/about-claude/pricing), and [Groq structured outputs](https://console.groq.com/docs/structured-outputs).

**Which is cheaper? Groq GPT-OSS 120B is cheaper at these standard uncached rates.** Actual bills can differ because tokenization, reasoning output, retries and prompt sizes differ. A larger parameter count does not automatically imply a higher hosted API price.

## What an interaction means in this application

One interaction means one user message or confirmation submitted to the backend, not an entire multi-turn booking conversation. If “100,000 interactions” instead means 100,000 complete conversations, the estimate must be multiplied by the observed turns and call mix per conversation.

The existing code does not call the model on every turn:

- A normal free-text booking request can require one interpretation call.
- A general knowledge question can require interpretation followed by evidence selection: two sequential calls.
- Recognized knowledge topics can bypass interpretation and call only the evidence selector.
- Confirmations, supported deterministic selections, resets and some rejected/no-evidence requests can avoid model calls.

Python renders the final knowledge answer. Its displayed text is not an additional model-generated completion. Input tokens still include instructions, JSON/schema overhead, conversational context and retrieved evidence. See [workflow.py](../app/workflow.py) and [groq_client.py](../app/groq_client.py).

## Monthly cost at 100,000 interactions

### Explicit assumptions

This is an illustrative traffic mix, not usage measured from the demo:

| Interaction type | Monthly interactions | Calls per interaction |
|---|---:|---:|
| Free-text booking/availability interpretation | 60,000 | 1 interpretation |
| General knowledge question | 20,000 | 1 interpretation + 1 evidence selection |
| Directly routed knowledge topic | 10,000 | 1 evidence selection |
| Deterministic/no-model turn | 10,000 | 0 |
| **Total** | **100,000** | **110,000 calls** |

Assume 2,000 input and 150 billed output tokens per interpretation, and 3,500 input and 100 billed output tokens per evidence selection. These are budget inputs to replace with observed provider usage; they are not token measurements. The baseline assumes no additional reasoning output beyond these totals, no retries, no caching and standard synchronous pricing.

```text
Interpretation calls = 60,000 + 20,000 = 80,000
Evidence calls      = 20,000 + 10,000 = 30,000

Input tokens  = 80,000 × 2,000 + 30,000 × 3,500 = 265,000,000
Output tokens = 80,000 ×   150 + 30,000 ×   100 =  15,000,000

Monthly cost = (input tokens / 1,000,000 × input rate)
             + (billed output tokens / 1,000,000 × output rate)
```

| Model | Input cost | Output cost | Monthly total | Cost / 1,000 interactions |
|---|---:|---:|---:|---:|
| GPT-OSS 120B / Groq | $39.75 | $9.00 | **$48.75** | **$0.4875** |
| Claude Haiku 4.5 / Anthropic | $265.00 | $75.00 | **$340.00** | **$3.40** |

Under these assumptions, Groq saves **$291.25/month**, approximately **85.7%**, and Haiku costs about **6.97 times as much**. This compares standard synchronous API charges, not consumer subscriptions or batch rates.

### Sensitivity: why the actual bill can differ

| Change from baseline | Estimated effect at the listed rates |
|---|---|
| 5% additional calls with the same token mix | Groq: $51.19; Haiku: $357.00, approximately. |
| Average input tokens double, output unchanged | Groq: $88.50; Haiku: $605.00. |
| 300 additional billed output tokens per call | 33M additional output tokens: Groq adds $19.80 (total $68.55); Haiku adds $165 (total $505). |
| Every interaction becomes a two-call knowledge request at the stated sizes | 550M input + 25M output tokens: Groq $97.50; Haiku $675.00. |

The extra-output scenario is especially relevant when budgeting reasoning behaviour: small visible JSON does not establish how many tokens the provider bills. The current GPT-OSS client requests low reasoning effort and caps completion tokens at 1,500; a cap is not an expected usage value. Capture actual usage before assuming the baseline output budget is sufficient. Token accounting and completion behaviour must be checked separately for each provider.

No cache discount is assumed without evidence of eligible cache hits. Hosting, PostgreSQL, OTP delivery, monitoring, taxes and support are excluded. There is no paid embedding call in the current local lexical retrieval implementation. This estimate is not the total cost of running the service.

## Latency at this volume

At 100,000 interactions over 30 days, average traffic is about 3,333 interactions/day or 2.31/minute. The assumed 110,000 model calls average 2.55/minute. These averages do not describe peak traffic or establish that a particular account's rate limits are sufficient.

The backend waits for complete validated JSON and does not stream a model answer. A useful planning equation is:

```text
Interaction latency ≈ backend/database work
                    + sum of sequential model-call latencies

Model-call latency ≈ network + queue/prefill time + generated tokens / generation rate
```

Groq's advertised generation rate suggests a potential advantage in the generation portion, but it is not an end-to-end SLA. The cited Anthropic page does not provide a matching numeric throughput benchmark. Therefore the following is explicitly a **hypothetical sensitivity estimate**, not a measured provider comparison:

- Use 0.10 seconds for non-model backend work.
- Assume 0.60 seconds of network/queue/prefill overhead per call for either provider.
- Use 500 tokens/second as Groq's advertised reference point.
- Use **100 tokens/second solely as an assumed Claude Haiku 4.5 scenario**, not a sourced performance claim.
- Use the baseline 150/100 generated-token budgets and exclude additional reasoning, cold starts, retries and congestion.

| Path | Groq reference scenario | Claude Haiku 4.5 hypothetical scenario |
|---|---:|---:|
| One interpretation | 0.10 + 0.60 + 150/500 = **1.00s** | 0.10 + 0.60 + 150/100 = **2.20s** |
| Interpretation + evidence selection | 0.10 + 1.20 + 250/500 = **1.80s** | 0.10 + 1.20 + 250/100 = **3.80s** |
| Direct evidence selection | **0.90s** | **1.70s** |
| No model call | **0.10s assumed** | **0.10s assumed** |
| Weighted mean for the stated traffic mix | **1.06s** | **2.26s** |

These numbers illustrate sensitivity to throughput. They do **not** establish that Groq is 2.1 times faster in this application. Actual output length, reasoning, input processing, provider load and deployment-region latency can change or reverse the result. No p95/p99 estimate is justified without measurement. Increasing monthly traffic does not inherently increase per-request latency until capacity, queues or limits become a bottleneck.

## Quality, integration and decision

| Consideration | Assessment for this project |
|---|---|
| Task quality | Compare date refinements, negation, intent routing and evidence relevance on the same evaluation set. No head-to-head result currently establishes a winner. Parameter count alone is insufficient. |
| Safety | Keep ownership, notice policy, confirmation and SQL execution in Python for both models. Structured JSON does not prove semantic correctness. |
| Current integration | Groq 120B is already configured. An Anthropic alternative requires a tested provider adapter/configuration, credentials, refusal/error handling and compatible request parameters; changing only the model name is not a verified migration. |
| Cost | Groq has lower listed rates. Actual token use, failed requests and extra clarification turns still determine cost per successfully completed task. |
| Latency | Groq has a published throughput reference; neither provider has been benchmarked head-to-head in the deployed app. Measure full-response latency and tail latency. |
| Operational fit | Check account quotas, peak-load behaviour, availability and data-handling requirements before deployment. Do not infer these from monthly token cost. |

**Recommendation:** retain the existing Groq integration for the take-home and evaluate Claude Haiku 4.5 as an alternative before switching. Haiku would need a demonstrated quality or operational benefit to justify its higher baseline cost; none has been established by a head-to-head evaluation. Choose the model with acceptable task accuracy and lower measured cost/latency per successful workflow, while retaining the same backend guardrails.

Run the [Part 6 evaluation cases](part-6-evaluation.md) against both using synthetic fixtures and identical prompts. Record valid-schema rate, correct intent/date/evidence selection, extra clarification turns, billed tokens, retries and end-to-end p50/p95 latency. Repeat at expected peak concurrency. Extend the client to record sanitized usage/timing metrics without recording secrets or patient text; this instrumentation is proposed, not implemented here.

This comparison does not switch models, modify credentials or make paid benchmark calls. Recheck linked prices before deployment.
