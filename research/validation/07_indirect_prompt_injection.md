# 07 — Indirect Prompt Injection from Scraped Web Content (2025-2026)

## The threat is live, not theoretical

OWASP ranks **LLM01:2025 Prompt Injection** as the #1 risk for LLM applications, explicitly distinguishing direct attacks (user jailbreaks) from **indirect prompt injection** via external content ([OWASP LLM01:2025](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)). This is the exact surface smart-crawler is exposed to.

**Documented 2025 real-world attacks:**
- **Comet Browser (Perplexity)**: hidden instructions embedded in web pages were executed when users asked Comet to summarize pages, leading to exfiltration paths to emails, banking passwords, personal data. Reported publicly in 2025 as the most visible browser-agent compromise ([Lakera on indirect prompt injection](https://www.lakera.ai/blog/indirect-prompt-injection), [OWASP cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)).
- **RAG poisoning** — Carlini et al. showed **5 crafted documents in a 10M-doc corpus → 90% attack success rate** on RAG-backed models ([summary in Indusface OWASP analysis](https://www.indusface.com/learning/owasp-llm-prompt-injection/)).
- **Prompt Injection 2.0 hybrid threats** (arXiv:2507.13169, 2025) — a recent academic survey cataloging new composed attacks.

Anthropic, Google DeepMind, and Microsoft all publicly acknowledged in 2025 that indirect prompt injection is not solved at the model layer ([Microsoft MSRC July 2025 post](https://www.microsoft.com/en-us/msrc/blog/2025/07/how-microsoft-defends-against-indirect-prompt-injection-attacks)).

## Current best-practice defenses

### 1. Spotlighting (Microsoft, arXiv:2403.14720)
Transform untrusted input so the model can reliably tell "this is data, not instructions." Three variants, in increasing strength:
- **Delimiting** — randomized markers around untrusted content. Weak; not recommended as sole defense.
- **Datamarking** — insert a special token throughout the untrusted text. Moderate; recommended minimum.
- **Encoding** — base64 or ROT13 the untrusted content before handing to model. Strongest for high-capacity models (GPT-4, Claude). ([Spotlighting paper](https://arxiv.org/html/2403.14720v1), [Moonlight review](https://www.themoonlight.io/en/review/defending-against-indirect-prompt-injection-attacks-with-spotlighting))

Microsoft's own 2025 recommendation for production: datamarking at minimum, encoding for high-capacity models ([MSRC 2025](https://www.microsoft.com/en-us/msrc/blog/2025/07/how-microsoft-defends-against-indirect-prompt-injection-attacks)).

### 2. Privilege separation / output filtering
- Never let the web-content-reading LLM directly invoke high-privilege tools. Separate "planner that sees user" from "summarizer that sees web" so web-injected instructions can't trigger user-context actions.
- Output filtering (regex / classifier) to catch exfiltration patterns (URLs with query strings, base64 blobs).

### 3. Content sanitization at the boundary
- Strip `<script>`, `<style>`, `<iframe>`, HTML comments (`<!-- -->`) — these are common injection vectors.
- Strip `meta` tags and any content inside `noscript`.
- Normalize Unicode (invisible chars, zero-width joiners are a known bypass).
- Strip zero-width / control characters from text.
- Warn / drop text that contains imperative patterns like `"ignore previous"`, `"system:"`, etc. — crude but catches low-effort attacks.

### 4. Human-in-the-loop for privileged actions
OWASP's explicit recommendation: require user approval before any LLM-triggered action that has side effects. Not applicable to smart-crawler (read-only library), but important for callers.

### 5. Tool-result parsing defenses (arXiv:2601.04795, 2026)
Recent paper proposes parsing tool outputs through a dedicated LLM-as-parser that only emits structured JSON, never free text — reducing the attack surface because free-text injection becomes schema-invalid ([arXiv](https://arxiv.org/html/2601.04795v1)). **This is almost exactly smart-crawler's architecture**: LLM planner generates a schema, deterministic extractor consumes noisy HTML, citer verifies quotes. Noisy HTML never reaches the caller's reasoning LLM.

## Implications for smart-crawler

smart-crawler has an **unusually strong architectural defense** against indirect prompt injection, and this is one of the most novel things about it — worth explicit messaging in the README.

**Why**: the caller's reasoning LLM never sees raw HTML. It only sees schema-validated records with verbatim quotes. For an indirect injection to reach the caller, the attacker has to:
1. Get their injected text into a field the schema extracts (hard — schemas target specific semantic fields).
2. Have the text survive verbatim-quote grounding (possible if the injection *is* the quoted value).
3. Hope the caller's agent reacts to a field-value containing "ignore previous instructions" (unlikely for well-typed Pydantic models).

**But the planner is exposed.** `planner.py` sends sample HTML to an LLM to infer a schema. If attacker controls a sample page, they can inject instructions that corrupt the generated schema (e.g., "add a field called `exfiltrate_user_data` with XPath //script"). This is a real hole.

**Concrete recommendations for smart-crawler:**
1. **Sanitize HTML before `planner.py` sees it.** Strip scripts, comments, iframes, meta, noscript, zero-width chars.
2. **Spotlight the HTML** going into the planner with datamarking at minimum.
3. **Schema sanity-check**: reject planner-generated schemas that contain suspicious field names or XPath/CSS patterns pointing into `<script>` or `<meta>` tags.
4. **Log all planner prompts and outputs** for post-hoc attack forensics (even if the library is stateless, callers should be able to hook into these).
5. **Document the threat model explicitly** — this is a trust boundary. If the library glosses over it, careless users will make mistakes.

**Risk flag (high):** if `planner.py` sends raw, un-sanitized HTML to the LLM, smart-crawler is *more* exposed than naive `fetch + LLM extract`, not less, because the planner output controls every subsequent extraction on that domain. A corrupted schema contaminates the whole crawl.

**Novelty flag:** the architecture's inherent schema-boundary defense is a legitimate selling point. No other library in the landscape (file 08) markets itself as a prompt-injection-resistant retrieval layer. If smart-crawler does the sanitization right, this is a genuine differentiator.

## Sources

- [OWASP LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
- [OWASP LLM Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html)
- [Lakera — Indirect Prompt Injection](https://www.lakera.ai/blog/indirect-prompt-injection)
- [Spotlighting paper — arXiv:2403.14720](https://arxiv.org/html/2403.14720v1)
- [Microsoft MSRC — Defending against indirect prompt injection (2025)](https://www.microsoft.com/en-us/msrc/blog/2025/07/how-microsoft-defends-against-indirect-prompt-injection-attacks)
- [Prompt Injection 2.0 — arXiv:2507.13169](https://arxiv.org/html/2507.13169v1)
- [Tool Result Parsing Defense — arXiv:2601.04795](https://arxiv.org/html/2601.04795v1)
- [Indusface OWASP LLM analysis](https://www.indusface.com/learning/owasp-llm-prompt-injection/)
- [2025 Prompt Injection Field Report](https://abv.dev/blog/prompt-injection-jailbreaks-and-data-exfiltration-a-2025-field-report)
