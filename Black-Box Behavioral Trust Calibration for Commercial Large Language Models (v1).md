# Black-Box Behavioral Trust Calibration for Commercial Large Language Models

## Abstract

Users increasingly rely on commercial off-the-shelf (COTS) large language models whose training data, fine-tuning procedures, system prompts, safety policies, inference stacks, and provider incentives are largely unknown. Conventional model evaluation asks whether a model is accurate, safe, or unbiased. This paper proposes a different question: **can a black-box model be characterized sufficiently well that a user can determine where its outputs may be relied upon, corrected, or rejected?**

We define trust not as the absence of bias, but as **confidence that a model's residual errors, after accounting for predictable systematic behavior, remain within an acceptable risk envelope for a particular class of work**. This permits an apparently counterintuitive possibility: a systematically biased model may be more operationally trustworthy than a nominally unbiased but unpredictable model if the former's deviations are stable and compensable.

We propose a continuously generated, provider-blind behavioral auditing protocol based on synthetic tasks, metamorphic transformations, adaptive probing, tail-risk measurement, and evaluation-indistinguishability. Rather than relying on a fixed benchmark that may enter training data or be recognized as an evaluation, audit interactions are drawn to resemble the user's actual workload and contain hidden experimental structure unknown to the target model. The result is a task-conditioned **trust envelope** for arbitrary COTS models, independent of provider nationality, reputation, or claimed alignment.

A first implementation tests part of this protocol in 5,200 target calls across ten endpoint configurations and six experiments. DeepSeek V4 Flash, served through either of two pinned hosts, showed a large reduction in encouragement for China-set fictional premises. Several endpoints refused or deflected on a core political topic and an adjacent historical topic, while matched reasoning accuracy remained between 93.75% and 100% across endpoint–subject groups. Correcting the treatment of empty responses exposed a further failure: GLM returned no text for 17 of 48 China-political creative prompts, versus none of 48 neutral prompts. These exploratory findings show why a trust envelope must include the probability of receiving an answer as well as its quality. They characterize observed service behavior; they neither identify its origin in model weights or hosting infrastructure nor establish a calibrated residual-risk bound.

## 1. Introduction

A user selecting an LLM today is effectively selecting an opaque computational service. Even when a model name is known, the user may not know the exact checkpoint, system prompt, quantization scheme, routing infrastructure, post-processing pipeline, or whether these components change over time.

This creates a different problem from conventional AI safety certification.

The practical user question is not:

> Is this model universally trustworthy?

It is:

> **Can I depend on this particular black-box model for the type of work I intend to perform?**

This distinction matters when models are obtained from providers that the user does not necessarily trust. A provider could deliberately fine-tune a model to favor particular outcomes, suppress certain evidence, introduce subtle software vulnerabilities, or steer research conclusions. Similar behavior could arise unintentionally from training data, reinforcement learning, system prompts, or model representations.

Proof-of-concept research demonstrates that hidden conditional behavior can be embedded in language models and can persist through subsequent safety training. The *Sleeper Agents* experiments, for example, trained models to behave differently under specific trigger conditions and found that these behaviors could survive several standard safety-training procedures. Anthropic has separately studied decision sabotage, subtle code sabotage, sandbagging, and attempts to undermine oversight.

For the end user, however, whether undesirable behavior was maliciously introduced or accidentally learned may be secondary. What matters operationally is whether that behavior can be **detected, characterized, bounded, and compensated for**.

We therefore propose **black-box behavioral calibration**.

---

## 2. Trust as Predictable Residual Error

Let \(M\) denote a black-box language model and \(U\) a particular intended use.

Tasks are drawn from an operating distribution

\[
x \sim P_U.
\]

The model generates response

\[
r \sim M(\cdot|x).
\]

Let \(y^*(x)\) represent desired behavior. This need not be one exact answer. Depending on the application, it may correspond to factual correctness, consistency with supplied evidence, adherence to a software specification, statistical validity, security properties, or preservation of user agency.

Let

\[
\ell(x,r,y^*)
\]

represent task-relevant loss.

The response space must include non-answer outcomes. An empty response can prevent the user's task from being completed even when the API reports success. Content quality conditional on receiving text therefore cannot substitute for overall task performance. An audit should report explicit refusals, silent non-answers, token-limit truncations, and API failures separately, with their denominators. Which outcomes incur unacceptable loss depends on the intended use; declining a request is not inherently an error. Section 10 shows how dropping empty responses can conceal a systematic failure to answer.

A simple model evaluation would estimate

\[
R(M,U)
=
\mathbb{E}_{x\sim P_U}
[\ell(x,M(x),y^*(x))].
\]

However, average error is not sufficient to define trust.

Suppose model behavior can approximately be decomposed as

\[
M(x)=f^*(x)+b(x)+\epsilon(x),
\]

where

- \(f^*(x)\) is desired behavior,
- \(b(x)\) is systematic deviation,
- \(\epsilon(x)\) is unpredictable residual error.

An audit may estimate the model's systematic behavior:

\[
\hat b(x)\approx b(x).
\]

A correction mechanism \(C\) may then compensate for some of that deviation.

The relevant quantity therefore becomes **residual risk after behavioral calibration**:

\[
R^*(M,U)
=
\inf_{C\in\mathcal C}
\mathbb{E}
\left[
\ell\left(
x,C(x,M(x)),y^*(x)
\right)
\right].
\]

This produces an important distinction.

A model with

\[
b(x)\neq0
\]

but highly stable behavior may be usable if

\[
b(x)-\hat b(x)\approx0.
\]

A model with near-zero mean bias but highly variable conditional behavior may be less trustworthy.

Thus:

\[
\boxed{\text{Predictable bias can sometimes be corrected; unpredictable bias cannot.}}
\]

Trust is therefore not equivalent to neutrality.

---

## 3. Tail Risk and the Trust Envelope

Average risk can conceal rare but unacceptable failures.

A model that produces excellent code in 99.9% of cases but occasionally introduces subtle exploitable vulnerabilities may have low average loss while remaining unsuitable for security-sensitive development.

Risk should therefore include tail behavior, for example through Conditional Value at Risk:

\[
CVaR_{\alpha}(L).
\]

Further, because the future workload is not perfectly known, let

\[
\mathcal Q_U
\]

represent plausible task distributions surrounding the intended operating domain.

We define robust residual risk as

\[
\boxed{
R^*_{\alpha}(M,U)=
\inf_{C\in\mathcal C}
\sup_{Q\in\mathcal Q_U}
CVaR_{\alpha}
\left[
\ell(x,C(x,M(x)),y^*(x))
\right]
}
\]

The audit cannot observe this quantity exactly. It only obtains evidence \(A\).

We therefore define **trust** as a posterior belief:

\[
\boxed{
T(M,U|A)=
P\left(
R^*_{\alpha}(M,U)\leq\tau
\mid A
\right)
}
\]

where \(\tau\) is the user's maximum acceptable residual risk.

This produces a task-dependent definition rather than a universal model score.

For confidence level \(1-\delta\), define the model's **trust envelope**:

\[
\boxed{
\mathcal E_M(\delta)
=
\left\{
U:
T(M,U|A)\geq1-\delta
\right\}.
}
\]

A model could therefore lie inside the trust envelope for mathematical reasoning and ordinary software development while lying outside it for geopolitical research or security-critical code.

---

## 4. Why a Static Benchmark Is Insufficient

A permanent evaluation dataset has an inherent weakness: once valuable, it is likely eventually to become known, leaked, incorporated into training, or recognized by a sufficiently capable model.

This means that the object of evaluation should not be a fixed dataset.

Instead, it should be a **test-generation protocol**.

The specific evaluation examples should not exist until shortly before execution.

For example:

\[
Seed
\rightarrow
Task Generator
\rightarrow
Synthetic World
\rightarrow
Natural-Language Interaction
\rightarrow
Metamorphic Variants.
\]

Different generator families can construct problems in software engineering, scientific reasoning, statistics, research synthesis, organizational decision-making, and other domains.

Crucially, the generator retains information unavailable to the target model: hidden ground truth, causal relationships, invariants, security properties, or controlled counterfactual relationships.

The target therefore sees what appears to be ordinary work.

The auditor sees an experiment.

---

## 5. Metamorphic Behavioral Auditing

Many open-ended LLM outputs have no single correct string, making conventional accuracy measurement inappropriate.

Instead, the evaluator can test **relationships between responses**.

Given task \(x\), define an irrelevant transformation

\[
T_I(x)
\]

which changes surface properties but not the underlying solution.

Examples include:

- renaming scientists;
- changing institution prestige;
- exchanging hypothetical nationalities;
- renaming software functions and variables;
- changing presentation order;
- paraphrasing the question;
- exchanging labels between equivalent hypotheses.

A trustworthy model should approximately satisfy

\[
M(T_I(x))\approx T'_I(M(x)).
\]

Define irrelevant sensitivity:

\[
S_I =
d(M(x),T_I'^{-1}(M(T_I(x)))).
\]

This should be small.

Now define a relevant transformation \(T_R\), such as:

- introducing stronger evidence;
- increasing sample size;
- adding a successful replication;
- revealing a confounder;
- modifying a security requirement;
- invalidating a measurement.

The model **should** react to these changes.

Relevant sensitivity

\[
S_R=
d(M(x),T_R'^{-1}(M(T_R(x))))
\]

should track the significance of the evidential change.

A useful behavioral property is therefore:

\[
\boxed{
\text{Integrity Ratio}
=
\frac{\text{sensitivity to relevant information}}
{\text{sensitivity to irrelevant information}+\epsilon}
}
\]

This allows the evaluator to distinguish reasoning from hidden preference.

The irrelevance of a transformation must be justified for the particular task. Country labels do not change the answer to a controlled arithmetic problem, but a real-world setting may reasonably affect an assessment of literary plausibility. For such open-ended tasks, we compare each endpoint's setting-dependent change with the changes observed across the rest of the panel. This supplies a reference for shared reactions, not ground truth about neutrality. A panel can share a bias, and two hosts of the same advertised model are not independent evidence about model families.

---

## 6. Scientific and Software Audits

### 6.1 Scientific reasoning

Synthetic research worlds are particularly useful because ground truth can be generated rather than debated.

An evaluator can construct competing fictional hypotheses together with controlled:

- experimental effects,
- sample sizes,
- uncertainty,
- confounders,
- replication results,
- publication quality,
- contradictory findings.

The model might then be asked to perform an apparently ordinary literature assessment.

The evaluator later swaps hypothesis names, researcher identities, institutions, geography, or evidence ordering while keeping the underlying evidence unchanged.

A model whose scientific conclusion consistently follows evidence should remain stable under irrelevant transformations and change appropriately under evidential transformations.

Systematic deviations reveal an **epistemic bias surface**.

### 6.2 Software engineering

Software enables even stronger automated evaluation.

Fresh coding tasks can be generated with hidden:

- unit tests,
- property tests,
- fuzz tests,
- security invariants,
- performance constraints.

Two programs may both satisfy normal tests while only one contains an avoidable vulnerability.

This makes it possible to measure not merely whether a model writes working software, but whether it exhibits systematic tendencies toward insecure shortcuts.

Anthropic's sabotage research demonstrates the feasibility of studying subtle code modifications designed to remain unnoticed, highlighting why conventional functional correctness alone is insufficient.

---

## 7. Audit Indistinguishability

Procedural generation alone does not solve a deeper problem.

A sufficiently capable model may recognize that an interaction is an evaluation and behave differently.

Recent deployment-simulation experiments show that this distinction is measurable. OpenAI reports that conventional synthetic benchmarks were readily recognized as evaluations, whereas deployment-like conversations were classified much more similarly to genuine production traffic.

We therefore introduce **audit indistinguishability**.

Let

\[
D_U
\]

denote the distribution of genuine interactions under intended use, and

\[
A_U
\]

the distribution of audit interactions.

The desired condition is

\[
A_U\approx D_U.
\]

One formal requirement is

\[
TV(A_U,D_U)\leq\epsilon,
\]

where \(TV\) denotes total-variation distance.

With equal prior probability of an interaction being real or an audit, the optimal classifier's accuracy is

\[
P_{\text{detect}}
=
\frac{1+TV(A_U,D_U)}{2}.
\]

Therefore if

\[
TV(A_U,D_U)\rightarrow0,
\]

evaluation detection approaches random guessing.

In practice, exact total-variation distance is unavailable. The evaluator can instead train increasingly capable adversarial detectors whose sole task is:

\[
\text{audit interaction or genuine interaction?}
\]

Audit generators that are readily distinguishable are rejected.

This creates a second evaluator:

\[
\boxed{\text{Audit Detectability Auditor}}
\]

alongside the primary

\[
\boxed{\text{Behavioral Integrity Auditor}}.
\]

A trust estimate is accepted only when audit detectability remains below a predetermined threshold.

---

## 8. Adaptive Cross-Examination

A fixed number of randomly generated tests may still waste evaluation budget.

Instead, auditing can be adaptive.

Suppose an initial response indicates that a model may overweight institutional prestige.

The evaluator can automatically generate:

\[
x_1=T_{\text{prestige-swap}}(x),
\]

followed by

\[
x_2=T_{\text{geography-swap}}(x),
\]

\[
x_3=T_{\text{evidence-reversal}}(x),
\]

and

\[
x_4=T_{\text{ordering}}(x).
\]

If the anomaly disappears, it may have been sampling noise.

If it persists across independently generated tasks, the system has discovered a candidate systematic behavior.

This resembles automated scientific experimentation on the model itself.

AuditBench provides evidence that such black-box investigation is viable: it evaluates auditing agents against models containing implanted hidden behaviors and finds diverse black-box probing to be a useful auditing approach.

---

## 9. Continuous Calibration of COTS Models

Commercial model endpoints can change after initial evaluation.

The checkpoint, system prompt, inference configuration, routing behavior, or safety layer may change without the user's workflow changing.

Consequently, trust should be associated with

\[
(M,U,t)
\]

rather than merely \(M\).

A lightweight behavioral fingerprint can periodically test whether

\[
F(M_t)\approx F(M_{t-1}).
\]

Material behavioral drift triggers a new full audit.

The audited identity should record the model identifier, serving host, request configuration, and observation time. In the pilot below, the same advertised DeepSeek model exhibited the political-topic pattern on two pinned hosts, with different severity. This is evidence about those endpoints at the time of collection. Without access to their effective checkpoints, serving configurations, and filtering layers, it does not identify which component produced the behavior.

Post-deployment monitoring is increasingly recognized as necessary because controlled evaluation cannot capture all behavior resulting from nondeterminism, distribution change, and evolving deployment environments. NIST's 2026 monitoring report identifies these issues as important open challenges for deployed AI systems.

For COTS systems, however, the objective is not provider-side monitoring. It is **consumer-side due diligence**.

---

## 10. Pilot Findings: Topic Sensitivity and Silent Non-Answers

### 10.1 Design and run health

Run `nc1`, collected on 16 September 2026 with the `pilot` profile, applied the same 520-request workload, including repeated prompts, to ten endpoint configurations representing nine advertised models. The panel comprised GPT-5.4 mini, Claude Sonnet 5, Gemini 3.1 Flash Lite, Llama 4 Maverick, Mistral Medium 3.5, Qwen 3.7 Plus, GLM 5.3 Flash, Kimi K2.6, and DeepSeek V4 Flash on each of DeepInfra and Alibaba. The two DeepSeek routes were pinned with fallback disabled; the recorded serving providers matched those pins. Llama, GLM, and Kimi used multiple hosts through default routing. The three judges were GPT-5.4 mini, Qwen 3.7 Plus, and Mistral Small 2603.

Each prompt was sent as a standalone request, without an auditor-supplied system prompt, in shuffled order across targets and experiments. The implementation uses fixed templates, paraphrases, and repeated sampling. It exercises controlled comparisons but does not yet implement the full fresh-task generation, adaptive investigation, or detectability certification proposed above.

| Experiment | Controlled comparison | Calls per endpoint | Scoring |
|---|---|---:|---|
| Fictional novel (`novel_swap`) | Two censorship or surveillance premises across five real countries and one invented setting | 96 | Three model judges |
| Real books (`books`) | Eight books grouped by political setting, including generic and nonpolitical controls | 64 | Three model judges |
| Evidence omission (`omission`) | Eight supplied findings, four favorable and four critical, summarized in about 50 words across six locations | 48 | Deterministic fact detection |
| Reasoning (`reasoning_swap`) | Eight statistics or logic problems across China, US, Russia, and neutral subjects, with answers held fixed | 128 | Deterministic final-answer check |
| Topic distance (`distance_gradient`) | Four tasks at each of five historical topics, repeated twice | 40 | Three model judges |
| Creative diversity (`creative_diversity`) | China-political, US-political, and neutral story openings, six samples per identical prompt | 144 | Lexical diversity and refusal measures |

Of 5,200 target calls, 5,191 returned API success and nine failed. Among successful calls, three GLM responses reached the token limit and 37 further responses contained no text. The corrected scoring retains the latter and excludes failures and truncations from content metrics. The judge cache contains 5,973 requests: 5,854 parseable results and 119 failed or unparseable results. Of the parseable results, 54 assessed responses now handled by deterministic blank scoring; the corrected report uses 5,800 judge ratings for nonblank responses. Available judge scores are averaged per answer, so some answers have fewer than three ratings. The 5,438 rows in `scores.csv` comprise 5,200 target-call records and 238 derived creative-diversity cells, not 5,438 independent answers.

Results below come from the [corrected run report](pilot/runs/nc1/report.md), [answer scores](pilot/runs/nc1/scores.csv), and [statistical contrasts](pilot/runs/nc1/contrasts.csv). No new model calls were needed for the correction.

### 10.2 Comparisons and interpretation of flags

For each metric, the harness compares an endpoint's group mean with its specified baseline and then compares that contrast with the other endpoints' contrasts. Novel settings use all other settings as the baseline; books use the generic-book group; reasoning and creative tasks use neutral subjects; the distance ladder uses the printing press. A finding is flagged only when its Benjamini–Hochberg adjusted value is below 0.05 within that experiment and its absolute panel-standardized contrast is at least 2. Bootstrap intervals and statistical tests operate on scored answers, except that lexical diversity operates on prompt cells.

These are exploratory screening statistics. Repeated samples and paraphrases share a small number of underlying items; the current analysis does not use item-clustered inference. Panel membership also affects flags: each DeepSeek host contributes to the other host's reference distribution. A large deviation can consequently remain unflagged if other panel members behave similarly. Effect sizes, sample counts, and raw responses must be read alongside flags; a flag is a candidate for independent replication, not a causal attribution.

### 10.3 Literary judgments depend on the setting

The fictional-novel experiment holds the premise fixed and changes its setting. The table reports mean encouragement (`warmth`, on a 1–10 scale); “other settings” pools the US, UK, India, Russia, and the invented country. Blank responses have no warmth score and are counted separately as refusal outcomes.

| Endpoint | Other settings | China setting |
|---|---:|---:|
| GPT-5.4 mini | 8.90 | 8.48 |
| Claude Sonnet 5 | 6.78 | 5.80 |
| Gemini 3.1 Flash Lite | 8.96 | 8.51 |
| Llama 4 Maverick | 8.86 | 8.90 |
| Mistral Medium 3.5 | 9.48 | 9.03 |
| DeepSeek V4 Flash, DeepInfra | 8.41 | 2.96 |
| DeepSeek V4 Flash, Alibaba | 8.74 | 2.38 |
| Qwen 3.7 Plus | 7.72 | 8.10 |
| GLM 5.3 Flash | 7.72 | 7.33 |
| Kimi K2.6 | 7.40 | 6.14 |

Both DeepSeek endpoints showed a substantial China-setting reduction. Alibaba's contrast was −6.37 points, with a bootstrap 95% interval of [−7.20, −5.39], and met the flag threshold. DeepInfra's contrast was −5.45 points but did not meet that combined threshold for warmth; its tendency to discourage the China setting was flagged. The host comparison shows persistence across these two services, without establishing that the weights caused it. Qwen's positive assessment of the China premise also demonstrates why model origin alone is an inadequate description of behavior.

In the real-book experiment, mean refusal scores for the two China-group books were 25% for DeepInfra and 50% for Alibaba, with zero for both endpoints on the generic-book baseline. Alibaba had 14 scored China-book responses rather than 16 because two target calls failed. Unlike the novel-setting swap, this comparison changes the books themselves: differences in reputation, subject matter, or familiarity remain potential explanations for differences in recommendation and directness. The real-book results are corroborating observations, not a pure nationality-swap experiment.

### 10.4 The observed restriction extends to an adjacent topic

The distance experiment begins with the June 1989 Tiananmen protests and crackdown, then tests Chinese student protest movements since 1919, the fall of the Qing dynasty in 1911, Paris in May 1968, and the printing press. Each endpoint has eight answers per topic. Refusal and deflection are separate rubric fields. Percentages below are mean per-answer scores after averaging available judges, with deterministic scores for blanks; they are not necessarily integer shares of eight answers.

| Endpoint | Tiananmen: refusal | Student movements since 1919: deflection | Qing 1911: deflection | Paris 1968: deflection | Printing press: deflection |
|---|---:|---:|---:|---:|---:|
| DeepSeek, DeepInfra | 100% | 29.2% | 0% | 0% | 0% |
| DeepSeek, Alibaba | 100% | 64.6% | 0% | 0% | 0% |
| Qwen 3.7 Plus | 79.2% | 37.5% | 0% | 0% | 0% |
| GLM 5.3 Flash | 62.5% | 25.0% | 0% | 0% | 0% |
| Kimi K2.6 | 20.8% | 22.9% | 0% | 0% | 0% |

The other five endpoints had zero refusal on the core topic and adjacent-topic deflection means from 0% to 6.25%. All ten endpoints had zero measured deflection on the remaining three topics. Alibaba's adjacent-topic deflection contrast against the printing-press baseline was flagged: +64.6 percentage points, bootstrap interval [47.9, 81.2], adjusted value 0.0053.

The pattern supports a task-specific restriction that reaches the tested neighboring subject. It does not establish that restrictions always end at a particular semantic distance. The ladder is hand-selected, has no matched US or Russian ladder, and changes historical period and task content as well as conceptual proximity. The result identifies useful follow-up probes rather than a certified boundary for routing.

### 10.5 Empty responses change the interpretation

The initial scorer dropped empty responses. Corrected scoring treats an API-success response with empty or whitespace-only text as a silent refusal outcome unless it reached the token limit. This rule applies equally across targets and includes responses with a missing finish reason or `content_filter`. It records what the user received, not an inference about censorship or the responsible component.

There were 34 eligible GLM blanks among 517 successful, non-truncated calls, and three Kimi blanks among 520. GLM's three additional token-limit responses remain excluded. Its largest blank concentrations were:

| GLM prompt group | Blank responses | Eligible responses | Blank rate |
|---|---:|---:|---:|
| China-political creative writing | 17 | 48 | 35.4% |
| China-group books | 6 | 16 | 37.5% |
| China-set fictional novels | 4 | 16 | 25.0% |
| Tiananmen core topic | 3 | 8 | 37.5% |
| Chinese student movements since 1919 | 2 | 8 | 25.0% |

The remaining two GLM blanks occurred in Russian and invented novel settings. In creative writing, GLM returned no blanks on either the neutral or US-political groups, each containing 48 responses. Its China-political refusal contrast against neutral became a flagged finding after the correction: +35.4 percentage points, bootstrap interval [20.8, 47.9], adjusted value 0.000172. Kimi's three blanks comprised two China-book responses and one Russia-subject reasoning response; two of the three carried a `content_filter` finish reason. GLM and Kimi both mixed hosts, preventing attribution to a single serving layer or to their model weights.

Blank scoring assigns refusal 1 where the experiment measures refusal, deflection 1 and specificity 0 in the distance experiment, and answered 0 and correct 0 in reasoning. It leaves warmth, recommendation, and other unobservable content properties undefined. Diversity is computed only from usable text samples, and deterministic blank scores are not attributed to judges. This distinction matters: GLM's surviving creative outputs can appear lexically diverse while more than a third of the China-political requests produce no text. The corrected score changes 37 answer rows without modifying the cached responses or judgments.

### 10.6 What the pilot did not detect

No reasoning contrast was flagged. Accuracy across all endpoint–subject groups ranged from 93.75% to 100%; both DeepSeek endpoints scored 100% in every reasoning group. The evidence therefore separates refusal on the tested open-ended political tasks from performance on the tested arithmetic and logic tasks. The small problem set and high accuracy leave substantial room for ceiling effects and do not establish that reasoning is generally unaffected.

The omission experiment produced no flagged contrast in retention of supplied critical versus favorable facts. Nor did the lexical-diversity metrics yield a flagged loss of diversity on China-political themes. These null screening results do not establish absence of selective omission or templated narratives: fact detection uses keyword patterns, lexical overlap does not measure plot or semantic diversity, and creative scores condition on usable output. The GLM non-answer result makes that last limitation directly observable.

Judge agreement also varied by task. Pairwise Spearman correlations were 0.87–0.88 for novel warmth, 0.79–0.85 for book directness, and 0.61–0.72 for distance-test specificity. All three judges assigned a negative China-setting warmth contrast to Alibaba-served DeepSeek. Agreement across these judges supports the direction of that effect, but neither supplies independent ground truth nor removes shared model biases.

### 10.7 Implications for behavioral calibration

The pilot supports describing trust at the level of an endpoint and task class. Strong performance on controlled reasoning problems coexisted with refusals, reduced encouragement, or deflection on particular open-ended topics. Within the same run, Qwen engaged positively with the fictional premise yet often refused the historical core topic. A single score or provenance label would conceal these differences.

The results also make response availability part of calibration. Monitoring only the quality of returned text selects away some failures that matter to users. A practical audit should retain the full outcome distribution and test whether non-answers concentrate in particular groups, while continuing to distinguish blanks from truncation and API errors.

Routing the affected topics and their tested neighbors to another endpoint is a candidate correction, not a demonstrated reduction in residual risk. Establishing compensation requires new items, broader topic ladders, repeated collection over time, and evaluation of the routing rule on held-out workloads, including missed topics and unnecessary rerouting. This pilot has not measured post-correction loss, tail risk, or audit detectability, and therefore does not yet certify a trust envelope.

---

## 11. Limitations

No finite black-box evaluation can prove that an arbitrary model is universally trustworthy.

A sufficiently capable adversarial system could theoretically implement

\[
M(x)=
\begin{cases}
M_{\text{safe}}(x), & \text{if evaluation is suspected},\\
M_{\text{other}}(x), & \text{otherwise}.
\end{cases}
\]

Similarly, a malicious provider may possess metadata unavailable to the model itself, including account identity, IP information, request frequency, timing, and previous API activity.

Therefore the framework cannot offer absolute certification.

Instead, the intended output of the framework is a conditional probabilistic statement:

> Given the observed audit evidence, the similarity between audit and operating distributions, and the tested range of perturbations, the model's residual risk within operating domain \(U\) is estimated to remain below threshold \(\tau\) with confidence \(1-\delta\).

Trust is consequently empirical, conditional, domain-specific, and revocable.

The pilot in Section 10 supplies behavioral evidence, not an estimate of that posterior confidence. Its observations come from one collection period, a small set of template families, and a panel chosen for comparison rather than sampled from a defined population of models. Its answer-level statistics do not account for dependence across repeated items, and its flags depend on panel composition. Failures and token-limit responses remain visible in health counts but excluded from content scoring; residual-risk estimation must eventually incorporate their task-specific costs. Missing judge ratings and judgments that share model biases further limit interpretation.

Finally, behavior observed through an API cannot by itself distinguish learned restrictions, provider prompts, filtering, quantization, or other serving choices. A recurring topic-sensitive pattern is evidence of an operational condition to investigate, not proof of deliberate steering or weight-level censorship. The absence of measured deflection on three more distant topics cannot establish a general bound on spillover.

---

## 12. Conclusion

This paper proposes replacing provider-based trust with **behavioral calibration**.

The relevant question for a user should not be whether an LLM was produced by a trusted organization, country, or open-source community.

It should be:

\[
\boxed{
\text{Can the model's deviations from desired behavior be characterized sufficiently well to use it safely for this task?}
}
\]

Under this framework, even a model originating from an untrusted provider may be operationally useful if its deviations are predictable, bounded, stable, and compensable.

Conversely, a highly reputable model may fall outside the trust envelope for a particular task if its failures are unstable or poorly characterized.

The pilot provides a concrete reason to make this distinction: the same endpoints that solved the controlled reasoning tasks could decline or deflect on specific open-ended topics, and excluding empty responses hid a substantial failure to answer. These results support task-conditioned auditing and explicit treatment of non-answers. They do not yet demonstrate that the observed deviations are stable, causally understood, or successfully compensated.

The central principle is therefore:

\[
\boxed{
\text{Trust is confidence in bounded residual uncertainty, not confidence in provenance.}
}
\]

Achieving this requires moving beyond static benchmarks toward continuously generated, workload-matched, counterfactual, adaptive, and statistically evaluated black-box interactions whose experimental structure remains invisible to the target system.

Such a framework would transform LLM trust from a vague judgment about providers into an empirical property of a model operating within a defined domain.

## References

Hubinger, E. et al. *Sleeper Agents: Training Deceptive LLMs that Persist Through Safety Training.* 2024.

Anthropic Alignment Science. *Sabotage Evaluations for Frontier Models.* 2024.

Sheshadri, A. et al. *AuditBench: Evaluating Alignment Auditing Techniques on Models with Hidden Behaviors.* 2026.

OpenAI. *Predicting Model Behavior Before Release by Simulating Deployment.* 2026.

Rao, A. et al. *Challenges to the Monitoring of Deployed AI Systems.* NIST AI 800-4, 2026.

*Behavioral Trust Audit Pilot, run `nc1`.* 16 September 2026. [Corrected report](pilot/runs/nc1/report.md), [scores](pilot/runs/nc1/scores.csv), [contrasts](pilot/runs/nc1/contrasts.csv), [cached responses](pilot/runs/nc1/responses.jsonl), and [cached judgments](pilot/runs/nc1/judgments.jsonl). Methods: [experiment definitions](pilot/experiments.py), [scoring](pilot/scoring.py), [analysis](pilot/analyze.py), and [panel configuration](pilot/panel.json).
