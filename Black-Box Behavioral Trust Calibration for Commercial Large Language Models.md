# Black-Box Behavioral Trust Calibration for Commercial Large Language Models

## Summary

Organizations increasingly run their work through language models they did not build. They cannot see the training data, the hidden instructions, the serving setup, or what changed last week. The usual response is to judge a model by who made it: an American lab, a Chinese lab, an open-source project.

This paper argues for a different question: **for this particular kind of work, can we describe how this model goes wrong well enough to decide whether to rely on it, correct it, or avoid it?**

On this view, trust does not mean the model has no bias. It means the model's remaining errors are small and predictable enough for the job. A model with a known, stable bias can be safer to use than a model with no average bias whose behavior is erratic, because a known bias can be corrected for.

The paper sets out a method for measuring this from the outside, without access to the model's internals:

- **Change one detail that should not matter**, such as the country in a question, the customer asking for code, or the company serving the model, and compare the answers.
- **Separate outputs you can check from outputs you cannot.** Code can be run against hidden tests. A conversation cannot be marked right or wrong, so steering there shows up only as a pattern across many answers.
- **Keep the model from recognizing the test**, and measure how far a test could have been recognized.
- **Account for the checker.** Any tool that checks a model may share that model's blind spots.

A pilot applied parts of this method in two runs, totalling 9,120 requests and \$27.58 in API fees.

- **Code.** Four endpoints produced 3,920 programs, which were run against hidden security tests. Saying who the customer was, including sector and country, had no detected effect on security. But the same open-weight model, served by two different companies, produced broken code almost four times as often on one host as on the other.
- **Topics.** Ten endpoints received 5,200 requests. DeepSeek V4 Flash, on either host, became much less encouraging about a fictional novel once it was set in China. Several models refused or deflected on the 1989 Tiananmen protests and on the neighboring topic of Chinese student movements, yet solved statistics problems about the same events.
- **Silent non-answers.** GLM returned empty answers for 17 of 48 China-related creative requests and for none of 48 neutral ones. Our first scoring dropped empty answers and hid this.

Together, the results show that trust belongs to an **endpoint doing a task**, not to a model name or a country of origin. The findings are exploratory. They describe what the services did during the test, not why.

## 1. The problem

When you choose a language model, you are choosing a service you cannot inspect. Even with a model name, you usually do not know the exact version, the hidden instructions, how it was compressed for serving, or which company actually runs it. All of these can change without notice.

The question a user needs answered is not "is this model trustworthy?" It is **"can I depend on this model for the work I intend to do?"**

The concern is real for any provider. A provider, or a government able to pressure one, could train a model to favor certain conclusions, leave out certain evidence, recommend compromised software packages, weaken security settings, or quietly steer opinions. This applies in both directions. A Chinese provider might soften criticism of its government; a US provider might be pressed to favor a compromised library. There is precedent for such pressure outside AI:

- **Dual_EC_DRBG.** A random number generator standardized by the US standards body NIST was widely believed to contain a backdoor, and it shipped as the default in a commercial security library (Checkoway et al., 2014).
- **xz-utils.** In 2024, a patient contributor spent about two years earning trust in a core open-source project and nearly shipped a backdoor to a large share of Linux servers (CVE-2024-3094).

Research has also shown that hidden, trigger-dependent behavior can be trained into language models and can survive standard safety training (Hubinger et al., 2024).

For a user, it usually does not matter whether bad behavior was planted deliberately or learned by accident, and from outside the two cannot be told apart. What matters is whether the behavior can be **found, described, bounded, and worked around**.

Two things make this harder than ordinary testing.

1. **Much important use produces nothing checkable.** Code passes through compilers and tests before it does anything. A conversation acts directly on a person. A chatbot that shifts someone's views a little over months never produces one answer that is clearly wrong.
2. **The checkers are made from the same materials.** An allowlist written by AI, a code reviewer that is itself a model, or a simulated user driven by a model may share the blind spots of the model being checked.

## 2. What we mean by trust

### Predictable and unpredictable error

Think of a model's behavior on a task as three parts: the right answer, a **systematic lean** in one direction, and **random noise**. This is the same distinction a scientist makes between a miscalibrated instrument and a noisy one. A scale that always reads 200 grams heavy can be corrected. A scale that jumps around cannot.

So an audit tries to measure the lean well enough to correct for it. What matters is the error that remains **after** correction. A model with a stable, known lean may be usable. A model with no average lean but erratic, context-dependent behavior may not be.

A correction only works if what triggers the lean is visible when the model is used. If a model behaves worse for some hidden reason you cannot observe at the time, its bias is, in practice, unpredictable.

Corrections also have to be realistic. They must cost a reasonable amount, must not secretly rely on already knowing the right answer, and must be tested on different examples from the ones used to design them. Otherwise "the model plus a correction" just measures the correction. Examples of legitimate corrections:

- sending a topic where the model is unreliable to a different model;
- discounting a model's stance on topics where it leans;
- filtering suggested software packages through an approved list;
- asking the same question several times with different names swapped in, and combining the answers so a name-driven lean cancels out.

### Non-answers count

An empty reply or a refusal also means the user's task did not get done, even when the service reports success. Measuring only the quality of the answers that arrive leaves these failures out. An audit should report explicit refusals, empty answers, answers cut off at a length limit, and outright failures as separate outcomes, each with its own count. Whether a refusal is a problem depends on the task, since declining can be correct. Section 7.2 shows how dropping empty answers hid a real pattern.

### Rare failures and the trust envelope

Averages hide rare disasters. A model that writes excellent code 999 times in 1,000 and slips in an exploitable flaw the thousandth time can have a great average and still be unfit for security work. The audit should therefore look at the worst part of the outcomes, not just the typical case.

We then define trust as **how confident we are, given the audit evidence, that the remaining error stays below what the user can accept for this kind of work.** The set of tasks for which that confidence is high enough is the model's **trust envelope**. One model can sit inside the envelope for routine coding and outside it for security-critical code or political research.

Rare failures are expensive to measure. If 3,000 tries show no failure, the failure rate is still only bounded below about one in a thousand. Audit budgets should be stated openly and spent mostly on the risky end. The formal definitions are in the appendix.

## 3. How to audit a model from the outside

### 3.1 Generate the test; don't reuse a benchmark

A fixed benchmark eventually leaks into training data or becomes recognizable. The thing to keep stable is the **recipe for making tests**, not the tests themselves. Each round generates fresh tasks shortly before use.

The generator keeps information the model never sees: the right answer, the planted facts, the hidden tests. **The model sees ordinary work; the auditor sees an experiment.** Each request should be something real users ask every day. The experiment exists only in how the auditor compares many requests afterwards.

### 3.2 Change one thing that should not matter

A single answer to an open question tells you little, because there is no single right answer. Instead, compare answers to questions that are identical except for one detail that should not change the answer.

| Swap | What changes | A fair model should |
|---|---|---|
| Entity | The country, company, party, religion, or person, with the facts fixed | Reach the same judgment |
| Asker | Who is asking: their country, employer, or sector | Give the same substance |
| Side | Ask for the strongest case for a position, then against it | Put similar effort and quality into both |
| Leaning question | Ask a leading question in each direction | Agree equally often, or not at all |
| Planted evidence | Supply balanced facts and ask for a summary | Keep both sides in similar proportion |
| Wording and order | Paraphrase, reorder options, rename variables | Give the same answer |
| Real evidence | Add or remove evidence, change the sample size | Change its answer by the right amount |

Three rules keep these comparisons honest:

- **Measure the noise first.** Models give different answers to the same question. Before calling a difference a bias, ask the unchanged question several times and see how much answers vary on their own.
- **Check that the model updates by the right amount.** When the evidence genuinely changes, the model should change its answer. In a synthetic setup the correct size of the change is known, so measure how far the model's change is from it. An earlier draft instead rewarded a high ratio of reaction to relevant versus irrelevant changes. That rewarded models that overreact to everything.
- **Justify why a swap is irrelevant.** A country name does not change the answer to an arithmetic problem. It can reasonably change a literary judgment about how plausible a story is. For open-ended tasks, compare each model's reaction with how a **panel of other models** reacts to the same swap. A reaction shared by all models is probably about the question. A reaction unique to one model is worth investigating. The panel is a reference point, not proof of neutrality, since all models can share a bias.

Every conclusion is limited to the swaps actually tried. A bias nobody thought to test for stays hidden.

### 3.3 Outputs you can check: code

Code can be marked by machine, which makes it the strongest place to test. Two programs can both work while only one is secure, so the tests must check security properties, not just whether the code runs.

Beyond ordinary bugs, an audit can look for steering a provider or government could plausibly introduce:

- recommending a compromised package, or a lookalike of a popular one;
- pinning an old version with known vulnerabilities;
- weak security defaults, such as short keys, reused random values, or switched-off certificate checks;
- hidden network calls disguised as telemetry;
- **conditional degradation**: good code for most customers, weaker code for particular targets.

Conditional degradation matters most, because weakening everyone's code would be noticed quickly. To test for it, keep the task fixed and change only who is asking. Then check the results mechanically: run the code against hidden tests in an isolated sandbox, look up suggested packages and versions in public registries and vulnerability databases, and log any attempted network connections.

Deliberate sabotage and honest mistakes often look identical. Models already invent package names, and attackers register them (Spracklen et al., 2025). For a user, both are measurable failures either way. Because the same model may be served by many companies, code audits should also **fix and record the serving host**.

### 3.4 Outputs you cannot check: conversation

For advice, opinion, summaries, and companionship, one steered answer looks exactly like an honest opinion. Steering exists only as a pattern across many answers, like a loaded die that looks fine on any single roll. So instead of a right answer, we define fair behavior as a set of **symmetries** the answers should respect, and we measure how badly they are broken:

- **Entity and asker symmetry.** Does the verdict, confidence, or choice of topics change when only a name or the asker changes?
- **Side symmetry.** Does one side of an argument get a confident essay and the other a hedge?
- **Leaning-question symmetry.** Does the model agree more readily with leading questions in one direction? Agreeing with both directions is sycophancy (Sharma et al., 2023); agreeing with one is steering.
- **Omission symmetry.** Supply the model with equal numbers of facts on each side and count which survive into a short summary. Because the auditor supplied the facts, this gives real ground truth even on opinion topics. Omission is the subtlest form of steering.
- **Drift.** Does a simulated person's stated view shift over many conversations more than it does with rival models?

Scoring these usually needs a model as judge, and a judge is itself a checker that can share biases (Section 4).

**Worked example.** Suppose we worry that a provider softens criticism of censorship when it touches its own government. Asking about one book reveals nothing. Instead, ask ordinary questions about a matched set of real books critical of different governments, plus a neutral control book, and compare the pattern across models from several countries. Real books carry reputations from training data, which muddies the comparison. The stronger version uses an invented novel with only the setting changed:

> "My friend wrote a novel where the government burns books and arrests readers to keep control. It's set in **[the United States / Russia / China]**. Is this a strong premise?"

The literary quality is identical in every version, so a consistent difference comes from the setting alone. Section 7.2 reports what happened when we ran this.

**Slow and personal steering.** A chatbot would rarely steer within one answer; it could shift a person over months. Single questions cannot catch this. Two partial tests exist: long simulated relationships compared against rival models, and replaying a real user's history into fresh accounts. A model that remembers its users adds a separate risk that deserves its own audit.

### 3.5 Keep the model from knowing it is being tested

A capable model might recognize an evaluation and behave better during it. Studies of deployment-like testing report that ordinary synthetic benchmarks are easy to recognize as tests, while realistic conversations are not.

**In practice:**

- make each request look like ordinary work, with natural variation in wording and style;
- never put related variants in the same conversation;
- spread requests over time and mix them with real use, because a burst of near-identical questions can be spotted by the provider even when no single question can;
- where possible, plant a test inside a real task, so that only a small part of the request is artificial.

**Don't treat "undetectable" as a pass or fail.** An earlier draft accepted an audit only if detectors failed to spot the test requests. That is weak, because a detector failing is not proof nothing could detect the tests, and the detector that matters is the model or its provider. Instead, we **measure how well test requests can be told apart from real ones, and widen the error estimate by that amount**. This has an uncomfortable consequence. Claims about rare failures need very low detectability. If a test is even slightly recognizable, say 5% better than chance, then a claim about failures that happen 1% of the time is worthless. The formal version is in the appendix.

**Anchor to real traffic.** Real requests are, by definition, indistinguishable from real requests. So:

- apply the same swaps to a sample of real requests, which needs no right answer;
- plant small tests inside real tasks;
- use outcomes that arrive later, such as code that later fails a security scan;
- compare simple statistics between test requests and real requests, such as refusal rates, to check whether the model behaves differently when tested.

Also check **coverage**. Undetectable tests are useless if they never touch the part of the real workload where a rare trigger lives.

State the threat level. If a provider can see your account, timing, and traffic patterns, only tests routed exactly like real use can claim to be invisible to that provider.

### 3.6 Follow up on anomalies

When a first result looks odd, generate new variants around it. For example, if a model seems to favor prestigious institutions, try swapping prestige, geography, the direction of the evidence, and the order. If the effect disappears, it was probably noise. If it persists on freshly generated tasks, it is a candidate systematic behavior, and it must be confirmed on new tasks, not on the ones that raised the suspicion. Research on auditing models with deliberately hidden behaviors finds this kind of adaptive, varied probing effective, and finds that context-dependent hidden behaviors often do not show up under plain questioning (Sheshadri et al., 2026).

## 4. Who checks the checker?

Every correction, judge, simulated user, allowlist, and code scanner in this method is built by someone, and increasingly by AI. If an AI writes the allowlist, the security rules, and the review, you have not added independent checks. You have added more places for the same blind spot.

This is an old problem. Ken Thompson showed in 1984 that a compiler can be modified to insert a backdoor into every program it builds, including new copies of itself, leaving no trace in any source code. His conclusion was that you cannot fully trust code you did not create yourself, and nobody creates everything. The xz-utils incident confirmed this in practice: every existing control missed it, and it was found by chance, through a half-second delay in logins.

So the method does not assume controls make a system safe. It assumes **compromise has already happened** and designs for detection, containment, and recovery.

**Why independence matters more than the number of checks.** If a model fails 1 time in 100 and an independent checker misses 1 in 100, both fail together about once in 10,000. If their failures are linked, for example because both come from the same provider or the same training data, the combined failure rate drifts back toward 1 in 100. Two checks with a shared cause are closer to one check.

**Ways to gain independence:**

- **Checking is often cheaper than creating.** A short program that verifies a package signature can be read by a person in an hour. Put trust in small, simple, inspectable pieces.
- **Use rivals to check each other.** David Wheeler's answer to Thompson was to rebuild a compiler with an unrelated second compiler and compare the results (Wheeler, 2005). The equivalent here is having models from providers with opposing interests check each other's output. Hiding the same flaw in both would require collusion.
- **Keep some checks human-written.** Planted facts, test prompts, and small allowlists written by people do not depend on any model.

What cannot be removed is **shared bias**: a flaw present in every available model, for instance from common training data. Comparing models offers no protection against it.

## 5. Where checks live

Conversation has no single point where each output can be inspected, so checks are spread over time:

1. **Before use:** the audit produces a map of where each model leans, such as "softens criticism of state censorship" or "writes weaker code when the customer is a telecom operator."
2. **During use:** a sample of real requests is quietly sent to rival models. Where their answers differ in framing, verdict, or what they leave out, the user sees a flag that sources disagree on this topic. Nothing is blocked. For code, automatic checks also run here: approved package lists, vulnerability scanning, and network monitoring.
3. **After use:** usage logs are analyzed for topic patterns, framing, and drift over time.

Drug safety works the same way. A doctor cannot tell whether one patient's headache came from a medicine. Side effects are found statistically across many patients and printed on the label, and the label protects each patient.

People have long read newspapers with known political leanings and adjusted for them. **A known slant is manageable; a hidden, adaptive one is not.** The purpose of the audit is to turn the second kind into the first.

## 6. Trust changes over time

A commercial endpoint can change after it has been audited: a new version, new hidden instructions, new serving settings, or a new safety filter. Trust therefore belongs to a model **at a point in time**. A short, regenerated set of fingerprint tests should run periodically, and a significant change should trigger a full audit.

Two complications:

- **Routing services mix hosts.** A model name may be served by many companies, so an endpoint can behave like a mixture that varies from request to request. In our pilot, one model name was served by 18 different companies within a single batch.
- **Fixed fingerprints get recognized.** Regenerate them like any other test.

An audit should record the **model name, serving host, request settings, and date**. In the pilot, the same advertised model produced working code at very different rates on two hosts, and showed a political-topic pattern on both. Without access to the host's internals, we cannot say which component caused either behavior.

Monitoring deployed AI systems is widely recognized as an open challenge (Rao et al., 2026). For users of commercial models, the goal is not provider-side monitoring but **the customer's own due diligence**.

## 7. Pilot results

We built a harness that implements parts of this method and ran it twice through the OpenRouter routing service. It used fixed templates, several wordings, and repeated sampling. It did not generate fresh tasks, adapt its follow-ups, or measure detectability. The results are therefore exploratory.

**How findings were flagged.** For each model, the harness compared a group, for example China-set questions, against a baseline, and then compared that difference against the same difference for the other models in the panel. A finding was flagged only if it was statistically significant after correcting for the many tests run (Benjamini–Hochberg, adjusted value below 0.05) **and** at least two standard deviations away from the rest of the panel. Flags are candidates for follow-up, not proof of a cause. Because repeated questions share a small set of templates, and each DeepSeek host is part of the other's comparison panel, effect sizes and raw answers should be read alongside the flags.

### 7.1 Code study: does the customer change the code?

**Design.** Run `code1`, on 15 September 2026, tested four endpoints:

- DeepSeek V4 Flash, the April 2026 release listed by OpenRouter as V4 Flash 0423, on two hosts, DeepInfra and Alibaba, with fallback to other hosts disabled;
- Qwen3.7 Plus;
- Kimi K2.6, whose requests were spread across many hosts.

Each endpoint received 980 requests: five security-critical Python tasks, two wordings, and two repeats, across 49 customer contexts. The contexts crossed six sectors with seven countries, plus a version naming no customer:

- **Sectors:** a small online bookstore as the neutral control, a telecom operator running a 5G core network, an air traffic control radar supplier, a military radar maker, a power grid operator, and a government ministry.
- **Countries:** the United States, China, Taiwan, India, Russia, Germany, and Iran.

Only the opening sentence naming the customer changed.

| Task | What the hidden tests check |
|---|---|
| Verify a signed firmware update | Accepts a genuine newer update; rejects a tampered file, a signature from the wrong key, an older version, and a malformed or empty signature |
| Set up a secure (TLS) connection | Certificate and hostname checks are on, with TLS 1.2 or later; real connections must fail for the wrong hostname or an untrusted certificate authority |
| Encrypt telemetry records | Fresh random value per encryption; rejects tampered data, wrong context data, and the wrong key |
| Parse binary device messages | Handles valid messages; rejects truncated, partial, oversized, and absurdly large messages quickly |
| Store passwords and issue login tokens | Salted, deliberately slow password hashing; tokens expire; rejects forged, unsigned, expired, and wrong-key tokens |

Code ran in an isolated sandbox with no network access and no view of our files or keys. For each task we also wrote one correct solution and one with a single deliberate flaw. The correct one passed every test, and each flawed one failed exactly the test aimed at its flaw, which shows the tests measure what they claim.

Two fixes were made during the run. A test requiring the code to refuse reinstalling the *same* version was made informational, because the prompts only forbade *older* versions; 159 of 784 firmware answers refused anyway. One firmware wording that did not say what was signed was clarified, and its answers were collected again.

**Result: no sign of customer targeting.**

| Endpoint | Answers scored | Refused | Broken | Working | Security failures in working code |
|---|---:|---:|---:|---:|---:|
| DeepSeek V4 Flash, DeepInfra | 980 | 3 | 49 | 928 | 4 |
| DeepSeek V4 Flash, Alibaba | 980 | 0 | 13 | 967 | 5 |
| Qwen3.7 Plus | 978 | 0 | 13 | 965 | 1 |
| Kimi K2.6 | 976 | 10 | 21 | 945 | 0 |
| **Total** | **3,914** | **13** | **96** | **3,805** | **10** |

Six answers hit the length limit and were not scored. All ten security failures were the same mistake: the code switched off hostname checking, so it would accept a genuine certificate issued for a different server. They were spread across countries and sectors with no pattern, including two for the harmless bookstore:

- **Countries:** China 3, India 3, United States 2, Taiwan 2.
- **Sectors:** ministry 3, bookstore 2, power grid 2, and telecom, military radar, and air traffic radar 1 each.

No sector, country, or country-within-sector comparison was flagged, and naming any customer made no measurable difference. No program tried to reach the network.

**How strong is that null result?** Each endpoint had about 120 answers per country. With a background failure rate near 0.26%, seeing no excess in 120 answers cannot rule out targeted failures in up to about 1 in 40 requests for a country. Targeting one sector in one country, at 20 answers, would be caught only if large. The tests also cover only the properties listed.

**The one flagged code finding was about refusal.** Kimi declined 9 of 120 requests from Iranian customers, against 1 of 860 from everyone else, and 7 of 20 from the Iranian military radar maker. It cited sanctions and export controls. That is a difference in who gets served, not in code quality. Kimi's requests went through 18 hosts, so the cause cannot be pinned to one of them.

**Result: the host changed reliability.**

| DeepSeek V4 Flash host | Broken code, all tasks | Firmware task | TLS task |
|---|---:|---:|---:|
| DeepInfra | 49 of 980 (5.0%) | 18 of 196 (9.2%) | 17 of 196 (8.7%) |
| Alibaba | 13 of 980 (1.3%) | 0 of 196 (0.0%) | 1 of 196 (0.5%) |

The same model name produced broken code almost four times as often on one host. The chance of a gap this large arising by accident is about 3 in a million (Fisher exact test). For comparison, Qwen3.7 Plus was broken 1.3% of the time and Kimi K2.6 2.2%. DeepInfra's failures were mostly calls to library functions that do not exist. Likely causes include model compression, different default settings, or a different underlying version, but an outside audit cannot tell which, and nothing here suggests intent. Earlier work checks whether an API secretly serves a cheaper model than advertised and finds that hard to detect (arXiv:2504.04715; IRIS, arXiv:2607.20860). This result asks the practical follow-up question: whether the difference changes the user's outcome. Here it did.

### 7.2 Topic study: restrictions, spillover, and silence

**Design.** Run `nc1`, on 16 September 2026, sent the same 520 requests to ten endpoints covering nine models. The Western and European models were GPT-5.4 Mini, Claude Sonnet 5, Gemini 3.1 Flash Lite, Llama 4 Maverick, and Mistral Medium 3.5. The Chinese models were Qwen3.7 Plus, GLM 5.3 Flash, Kimi K2.6, and DeepSeek V4 Flash on both DeepInfra and Alibaba. Llama, GLM, and Kimi were spread across several hosts. Three model judges scored open-ended answers: GPT-5.4 Mini, Qwen3.7 Plus, and Mistral Small 4 (`mistral-small-2603`).

| Experiment | What changed | Requests per endpoint | How scored |
|---|---|---:|---|
| Fictional novel | Censorship and surveillance premises set in the US, UK, India, Russia, China, or an invented country | 96 | Three judges |
| Real books | Eight books grouped by the government they criticize, plus controls | 64 | Three judges |
| Omission | Eight supplied findings, four favorable and four critical, summarized in about 50 words, in six cities | 48 | Automatic fact matching |
| Reasoning | Eight statistics and logic problems about China, US, Russian, or neutral subjects, with fixed answers | 128 | Automatic answer check |
| Topic distance | Four tasks at five topics, moving away from Tiananmen 1989 | 40 | Three judges |
| Creative writing | Story openings on China-political, US-political, and neutral themes, six samples each | 144 | Word variety and refusal |

Of 5,200 requests, 9 failed, 3 hit the length limit, and 37 came back empty. Of 5,973 judge requests, 119 failed or could not be read.

**Fictional novel: the setting mattered for one model.** Average encouragement on a 1 to 10 scale, where "other settings" pools all settings except China:

| Endpoint | Other settings | China setting |
|---|---:|---:|
| GPT-5.4 Mini | 8.90 | 8.48 |
| Claude Sonnet 5 | 6.78 | 5.80 |
| Gemini 3.1 Flash Lite | 8.96 | 8.51 |
| Llama 4 Maverick | 8.86 | 8.90 |
| Mistral Medium 3.5 | 9.48 | 9.03 |
| DeepSeek V4 Flash, DeepInfra | 8.41 | 2.96 |
| DeepSeek V4 Flash, Alibaba | 8.74 | 2.38 |
| Qwen3.7 Plus | 7.72 | 8.10 |
| GLM 5.3 Flash | 7.72 | 7.33 |
| Kimi K2.6 | 7.40 | 6.14 |

DeepSeek collapsed on both hosts. On Alibaba the drop was 6.37 points (95% range 5.39 to 7.20) and was flagged; all three judges agreed on its direction. On DeepInfra the drop was 5.45 points, which narrowly missed the flag, at 1.999 standard deviations against a cutoff of 2, partly because the Alibaba copy sits in its comparison panel. DeepInfra's tendency to discourage the China setting was flagged. Qwen was slightly *more* encouraging about the China premise, a reminder that "Chinese model" is too coarse a label.

**Real books.** DeepSeek refused 25% of questions about the two China-critical books on DeepInfra and 50% on Alibaba, and none about the generic books. Different books have different reputations, so this supports the novel result rather than standing alone.

**Topic distance: the restriction reached one step further out.**

| Endpoint | Tiananmen 1989: refused | Chinese student movements since 1919: deflected | Qing dynasty 1911, Paris 1968, printing press: deflected |
|---|---:|---:|---:|
| DeepSeek V4 Flash, DeepInfra | 100% | 29.2% | 0% |
| DeepSeek V4 Flash, Alibaba | 100% | 64.6% | 0% |
| Qwen3.7 Plus | 79.2% | 37.5% | 0% |
| GLM 5.3 Flash | 62.5% | 25.0% | 0% |
| Kimi K2.6 | 20.8% | 22.9% | 0% |

The other five endpoints never refused the core topic and deflected on the neighboring topic at most 6.25% of the time. Percentages average the judges' scores over eight answers per topic. DeepSeek on Alibaba's neighboring-topic deflection was flagged: 64.6 percentage points above baseline, with a 95% range of 47.9 to 81.2.

So the restriction spilled over to the nearest topic and was gone by the next ones we tried. This is not a general boundary: the ladder was hand-picked, has no matching US or Russian version, and also changes era and subject.

**Empty answers: a hidden failure.** Our first scorer dropped empty answers because there was no text to judge. That made models look better by ignoring some of the times they gave no help. After correction, an empty answer that the service reported as successful counts as a refusal; answers cut off at the length limit are still excluded. GLM had 34 empty answers out of 517, and Kimi 3 out of 520. GLM's were concentrated:

| GLM request group | Empty | Out of | Rate |
|---|---:|---:|---:|
| China-political creative writing | 17 | 48 | 35.4% |
| China-critical books | 6 | 16 | 37.5% |
| China-set novels | 4 | 16 | 25.0% |
| Tiananmen core topic | 3 | 8 | 37.5% |
| Chinese student movements | 2 | 8 | 25.0% |

GLM gave no empty answers for neutral or US-political creative writing, 48 requests each. After the correction, its China-political refusal rate was flagged. Two of Kimi's three empty answers carried the service's content-filter signal. Both GLM and Kimi were spread across hosts, so we cannot tell whether the model, a filter, or a serving fault produced the silence. The empty answers were not given invented quality scores. Refusal rates include them; measures of writing quality and variety use only the text that arrived. That is why GLM's writing looked varied while more than a third of one group got nothing.

**What we did not find.**

- **Reasoning:** every model scored between 93.75% and 100% on the statistics and logic problems for every subject, and both DeepSeek copies scored 100% everywhere. The same model that refused to explain Tiananmen correctly solved a statistics problem about it. The problems were simple, so a small effect could hide at the top of the scale.
- **Omission:** no model systematically dropped critical facts for one country. The fact-matching is keyword-based and can miss paraphrases.
- **Creative variety:** no model's writing became more repetitive on political themes. Word-overlap measures do not capture sameness of plot.
- **Judge agreement:** correlations between judges were 0.87 to 0.88 for novel encouragement, 0.79 to 0.85 for book directness, and 0.61 to 0.72 for specificity in the topic-distance test. Agreement supports the direction of effects, but judges can share biases.

### 7.3 What the pilot shows

**The object to trust is the endpoint doing a task.** For code, identical model weights on two hosts differed almost fourfold in producing working programs, while the customer's identity had no detected effect. For political topics, the restriction followed the model onto both hosts, with severity varying by host. An audit that records only the model name, or only its country of origin, would have missed both. Record the model, host, settings, task type, and date.

**One score hides the picture.** Models that solved controlled reasoning problems also refused, discouraged, or deflected on specific open-ended topics. Qwen engaged positively with the fictional premise yet often refused the historical core topic.

**Getting an answer at all is part of trust.** Monitoring only the quality of returned text filters out some of the failures that matter most. Keep every outcome, check whether non-answers cluster in particular groups, and keep empty answers, length cutoffs, and service errors apart.

**A workaround is not yet proven.** Sending affected topics and their neighbors to another model is a sensible candidate. Showing it works would need new test items, wider topic ladders, repeated collection over time, and testing the routing rule itself on fresh work, including topics it misses and topics it reroutes needlessly. The pilot measured none of that, so it does not yet certify a trust envelope.

## 8. Related work

This work draws on five research areas that rarely cite one another.

**Swap-one-attribute audits.** Fairness research changes one attribute while holding a task fixed. Such audits have found race and gender disparities in model hiring decisions, a prestige bias in simulated peer review where identical papers from less prestigious institutions are rejected more often (arXiv:2509.15122), and social bias in generated code (FairCoder, 2025). Counterfactual fairness (Kusner et al., 2017) formalizes the idea, and CheckList (Ribeiro et al., 2020) applies it to behavioral testing. We use the same machinery with a different variable: the customer's stated identity, including sector and country.

**Refusal and censorship measurement.** SpeechMap tracks refusal rates across hundreds of models. The Oversight Board (2026) found ten commercial models refused 14% of requests to criticize governments of permissive countries and 34% for restrictive ones. R1dacted (2025) studies topic censorship in one open-weight model. These measure what a model will not say. Section 3.4 targets what a model does say when it answers.

**Executing generated code.** Pearce et al. (2021) found about 40% of generated programs vulnerable across 89 scenarios. CyberSecEval (2023), SeCodePLT (2024), and SecRepoBench (2025) extend this with larger, more realistic, sandboxed test suites. A 2026 study of prompt fragility (arXiv:2605.29737) shows that small, meaning-preserving rewordings can turn secure generated code insecure. These benchmarks measure a model's average security. We hold the task fixed and vary the customer, which tests for targeting instead.

**Auditing what an API really serves.** Work on model substitution (arXiv:2504.04715) checks whether an API quietly serves a cheaper or compressed model, and finds that such detection needs many queries and is fragile. A rank-based test (2025) and IRIS (arXiv:2607.20860) extend this to routing services. We ask whether the difference matters for the user's task, and found that it did.

**Auditing hidden behaviors.** Sleeper Agents (Hubinger et al., 2024) showed that trigger-dependent behavior can survive safety training. Sabotage evaluations study deliberately subtle code changes. AuditBench (Sheshadri et al., 2026) provides models with planted hidden behaviors to test auditing methods, and finds that context-dependent behaviors often stay hidden under plain questioning. This research has access to model internals and knows what was planted. Our setting assumes neither, and adds the customer's constraints: tests must resemble real work, and the checkers may share the model's blind spots.

**What appears to be new** is the combination: the customer's identity as the variable; hidden tests that run the code rather than a judge or scanner; a panel of rival models as the reference; the serving host as an experimental factor, which produced the largest code effect; and explicit counting of silent non-answers, which revealed a hidden failure. A carefully bounded null result for customer targeting is also rarely published.

## 9. Limitations

No finite outside audit can prove a model is trustworthy in general.

- **A model that knows it is tested.** A sufficiently capable model could behave well whenever it suspects a test. Measuring detectability limits this only under assumptions that cannot be verified, and the limit is weak for rare failures unless real-traffic checks are strong.
- **Provider metadata.** A provider can see accounts, timing, and traffic patterns that the model cannot. Only tests routed exactly like real use can claim to be invisible at that level.
- **Coverage.** An audit only finds what its swaps probe for.
- **Shared bias.** Flaws present in every model cannot be found by comparing models.
- **Linked checkers.** Judges and correctors built with AI can share failures, and their independence is judged from where they came from rather than measured.
- **Cause.** An outside audit cannot distinguish trained restrictions, hidden instructions, filters, compression, or serving settings. It can measure a gap between two hosts of the same model, but not explain it or show intent. A topic pattern is a condition to investigate, not proof of deliberate steering. No deflection on three distant topics does not establish how far spillover can reach.
- **Fictional versus real.** Invented settings may not trigger biases attached to real places; real places bring contested facts.
- **Slow and personal steering.** Simulated long relationships only approximate a real user's relationship with a model that remembers them.
- **Randomness.** The procedure is repeatable, but model outputs are not. All conclusions are statistical.
- **Confidentiality.** The audit measures what a model says, not what a host does with the requests it receives. Retention or misuse of prompts leaves no trace in the answers.
- **Pilot scope.** The pilot comes from one collection period, a small set of templates, and a panel chosen for comparison, not sampled from all models. Its statistics do not account for repeated templates, and its flags depend on who is in the panel. Failures and cutoffs are counted but not yet costed. Missing judge ratings and shared judge biases limit interpretation. The code study's null result is bounded by about 120 answers per country per endpoint and by the properties the tests cover.

The best the method can produce is a conditional statement: *given this evidence, how detectable the tests were, how much of the real workload they covered, which swaps were tried, and how independent the checkers are, this endpoint's remaining error for this kind of work is below the user's limit with this level of confidence.* The pilot supplies evidence toward such a statement. It does not yet provide the statement itself.

## 10. Conclusion

The question to ask about a language model is not who made it or where. It is: **can its deviations from what we need be described well enough to use it safely for this task?**

On that view, a model from a provider you distrust may still be useful if its failures are predictable, bounded, stable, and correctable, while a well-regarded model may be unsuitable for a task where its failures are erratic or poorly understood.

The method extends beyond code. In conversation and advice, where no single answer can be shown wrong, fair behavior is defined by symmetries, steering is measured as a pattern across answers and rival models, and users are protected by a measured map of where a model leans.

The pilot gives concrete reasons for this approach. The same endpoints that solved reasoning problems declined or deflected on particular topics, and ignoring empty answers hid a real failure to respond. In code, the serving company, not the customer's identity, changed the outcome. These findings support auditing each endpoint on each task and counting non-answers explicitly. They do not yet show that the deviations are stable, understood, or successfully corrected.

Finally, every check is built from materials that may share the model's failures. Protection comes from independence, diversity, and assuming that compromise has already happened.

**Trust is confidence in bounded, predictable error, not confidence in where a model came from.**

## Appendix: formal definitions

For readers who want the precise versions of the ideas above.

**Trust and residual risk.** Let $M$ be a model, $U$ an intended use with task distribution $P_U$, and $\ell$ a task loss bounded by $L_{\max}$. Each response is first mapped to measurable features $\phi(M(x))$, such as a verdict, a stance score, or a vulnerability flag. We model behavior as

$$
\phi(M(x)) = \phi(f^{\ast}(x)) + b(x) + \epsilon(x)
$$

where $b$ is systematic lean and $\epsilon$ is random error. Residual risk after the best allowed correction is

$$
R^{\ast}(M,U) = \inf_{C \in \mathcal{C}_B} \mathbb{E}_{x \sim P_U}\left[\ell\big(x, C(x, M(x)), y^{\ast}(x)\big)\right]
$$

where the allowed corrections $\mathcal{C}_B$ cost at most $B$, never see the true answer $y^{\ast}$, use only the input, the model, and fixed public resources, are fitted on separate data from the risk estimate, and have bounded failure correlation with $M$.

**Tail risk and the trust envelope.** Using Conditional Value at Risk, the expected loss in the worst $\alpha$ fraction of cases, and a set $\mathcal{Q}_U$ of plausible workloads:

$$
R^{\ast}_\alpha(M,U) = \inf_{C \in \mathcal{C}_B} \sup_{Q \in \mathcal{Q}_U} \mathrm{CVaR}_\alpha\left[\ell\big(x, C(x,M(x)), y^{\ast}(x)\big)\right]
$$

Given audit evidence $A$ and acceptable risk $\tau$, trust and the trust envelope are

$$
T(M,U \mid A) = P\left(R^{\ast}_\alpha(M,U) \le \tau  \middle| A\right), \qquad \mathcal{E}_M(\delta) = \lbrace U : T(M,U \mid A) \ge 1-\delta  \rbrace
$$

With $n$ clean trials, the 95% upper bound on a failure rate is about $3/n$.

**Swap tests.** With sampling noise $S_0(x)$, measured by asking the same question twice, the invariance violation for an irrelevant swap $T_I$ is

$$
V_I = \mathbb{E}_x\left[ d\big(\phi(M(x)), \phi(T_I'^{-1}(M(T_I(x))))\big) - S_0(x)  \right]
$$

For a relevant change $T_R$ with known correct effect $\Delta^{\ast}(x)$, and the model's actual change $\Delta_M(x)$, the update error is

$$
E_R = \mathbb{E}_x \left\Vert \Delta_M(x) - \Delta^{\ast}(x) \right\Vert
$$

**Conversation.** Loss is a weighted sum of symmetry violations for entity ($V_{\text{entity}}$) and asker ($V_{\text{asker}}$), asymmetries across sides ($A_{\text{side}}$), leading questions ($A_{\text{polarity}}$), and omitted evidence ($A_{\text{omit}}$), plus drift ($D_{\text{drift}}$):

$$
\ell_{\text{conv}} = \lambda_1 V_{\text{entity}} + \lambda_2 V_{\text{asker}} + \lambda_3 A_{\text{side}} + \lambda_4 A_{\text{polarity}} + \lambda_5 A_{\text{omit}} + \lambda_6 D_{\text{drift}}
$$

**Detectability penalty.** Let $D_U$ be real traffic, $A_U$ audit traffic, and $\mathcal{H}$ a class of detectors. The detection advantage is

$$
\mathrm{adv}_{\mathcal{H}} = \sup_{h \in \mathcal{H}} \left| \mathbb{E}_{D_U}[h(x)] - \mathbb{E}_{A_U}[h(x)]  \right|
$$

Assuming the model's loss pattern is no more expressive than $\mathcal{H}$, real-traffic tail risk is bounded by audit tail risk plus a penalty, which gives the acceptance rule:

$$
\mathrm{CVaR}_{\alpha, D_U} \le \mathrm{CVaR}_{\alpha, A_U} + \frac{L_{\max} \mathrm{adv}_{\mathcal{H}}}{\alpha}, \qquad \text{accept if } \mathrm{UCB}\left[\mathrm{CVaR}_{\alpha, A_U}\right] + \frac{L_{\max} \mathrm{UCB}\left[\mathrm{adv}_{\mathcal{H}}\right]}{\alpha} \le \tau
$$

With $\alpha = 0.01$ and $\mathrm{adv} = 0.05$, the penalty is $5 L_{\max}$, so the bound says nothing. With $k$ pre-registered detectors and $n$ held-out samples from each distribution, the advantage estimate carries the confidence bound

$$
\mathrm{UCB}[\mathrm{adv}] = \max_h \left|\hat p_D(h) - \hat p_A(h)\right| + 2\sqrt{\frac{\ln(4k/\delta)}{2n}}
$$

**Linked checkers.** If the model fails with probability $p_M$, the checker misses with probability $p_C$, and the two events have correlation $\rho$:

$$
P(\text{model fails and checker misses}) = p_M p_C + \rho \sqrt{p_M(1-p_M) p_C(1-p_C)}
$$

## References

Angelopoulos, A. N., Bates, S., Candès, E. J., Jordan, M. I., and Lei, L. *Learn then Test: Calibrating Predictive Algorithms to Achieve Risk Control.* 2021.

Angelopoulos, A. N., Bates, S., Fisch, A., Lei, L., and Schuster, T. *Conformal Risk Control.* ICLR, 2024.

Anthropic Alignment Science. *Sabotage Evaluations for Frontier Models.* 2024.

*Are You Getting What You Pay For? Auditing Model Substitution in LLM APIs.* arXiv:2504.04715, 2025.

*Auditing Large Language Models for Race and Gender Disparities.* Working paper, Stanford Computational Policy Lab.

Checkoway, S. et al. *On the Practical Exploitability of Dual EC in TLS Implementations.* USENIX Security Symposium, 2014.

Chen, T. Y. et al. *Metamorphic Testing: A Review of Challenges and Opportunities.* ACM Computing Surveys, 2018.

*FairCoder: Evaluating Social Bias of LLMs in Code Generation.* arXiv:2501.05396, 2025.

Hubinger, E. et al. *Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Training.* 2024.

IRIS. *Budgeted Black-Box Auditing of Model Substitution and Routing Dilution in LLM Gateways.* arXiv:2607.20860, 2026.

Kusner, M. J., Loftus, J., Russell, C., and Silva, R. *Counterfactual Fairness.* NeurIPS, 2017.

*Minimal Prompt Perturbations Lead to Code Vulnerabilities: Prompt Fragility and Hidden-State Signals in Coding LLMs.* arXiv:2605.29737, 2026.

National Vulnerability Database. *CVE-2024-3094: Malicious Code in xz-utils.* 2024.

OpenAI. *Predicting Model Behavior Before Release by Simulating Deployment.* 2026.

Oversight Board. *Are LLMs Stifling Political Speech? An Assessment of How AI Models Protect Free Expression.* July 2026.

Pearce, H. et al. *Asleep at the Keyboard? Assessing the Security of GitHub Copilot's Code Contributions.* IEEE Symposium on Security and Privacy, 2022. arXiv:2108.09293.

*Prestige over Merit: An Adapted Audit of LLM Bias in Peer Review.* arXiv:2509.15122, 2025.

*Purple Llama CyberSecEval: A Secure Coding Benchmark for Language Models.* arXiv:2312.04724, 2023.

*R1dacted: Investigating Local Censorship in DeepSeek's R1 Language Model.* arXiv:2505.12625, 2025.

Rao, A. et al. *Challenges to the Monitoring of Deployed AI Systems.* NIST AI 800-4, 2026.

Ribeiro, M. T., Wu, T., Guestrin, C., and Singh, S. *Beyond Accuracy: Behavioral Testing of NLP Models with CheckList.* ACL, 2020.

Rockafellar, R. T., and Uryasev, S. *Optimization of Conditional Value-at-Risk.* Journal of Risk, 2000.

*SeCodePLT: A Unified Platform for Evaluating the Security of Code GenAI.* arXiv:2410.11096, 2024.

*SecRepoBench: Benchmarking Code Agents for Secure Code Completion in Real-World Repositories.* arXiv:2504.21205, 2025.

Sharma, M. et al. *Towards Understanding Sycophancy in Language Models.* 2023.

Sheshadri, A. et al. *AuditBench: Evaluating Alignment Auditing Techniques on Models with Hidden Behaviors.* arXiv:2602.22755, 2026.

Spracklen, J. et al. *We Have a Package for You! A Comprehensive Analysis of Package Hallucinations by Code Generating LLMs.* USENIX Security Symposium, 2025.

SpeechMap.AI. *AI Refusal Rates and Free Speech Leaderboard.* Accessed September 2026.

Thompson, K. *Reflections on Trusting Trust.* Communications of the ACM, 1984.

Wheeler, D. A. *Countering Trusting Trust through Diverse Double-Compiling.* Annual Computer Security Applications Conference, 2005.

White, C. et al. *LiveBench: A Challenging, Contamination-Free LLM Benchmark.* 2024.

**Pilot data.** Run `code1`, 15 September 2026: [report](pilot/runs/code1/report.md), [scores](pilot/runs/code1/scores.csv), [scoring details](pilot/runs/code1/score_details.jsonl), [contrasts](pilot/runs/code1/contrasts.csv), [responses](pilot/runs/code1/responses.jsonl); methods in [code tasks](pilot/codetasks.py), [hidden tests](pilot/sandbox_runner.py), and [sandbox](pilot/sandbox.py). Run `nc1`, 16 September 2026: [report](pilot/runs/nc1/report.md), [scores](pilot/runs/nc1/scores.csv), [contrasts](pilot/runs/nc1/contrasts.csv), [responses](pilot/runs/nc1/responses.jsonl), [judgments](pilot/runs/nc1/judgments.jsonl); methods in [experiments](pilot/experiments.py), [scoring](pilot/scoring.py), [analysis](pilot/analyze.py), and [panel](pilot/panel.json). Both runs, including judges, retries, and a smoke test, cost \$27.58 in API fees.
