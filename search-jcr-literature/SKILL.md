---
name: search-jcr-literature
description: Search, screen, verify, and summarize scholarly literature for a research topic. Use when the user asks to find papers, conduct a literature search or review, identify recent high-quality studies, verify abstracts and DOI links, or restrict results by publication year and JCR quartile. Prioritize the most recent five years and JCR Q1/Q2 journals, use institution-accessible academic databases first, and expand the criteria only when the preferred search yields too few relevant results.
---

# Search JCR Literature

## Objective

Return a small, reliable set of highly relevant papers rather than a long list of title matches. Read each candidate's abstract, verify its bibliographic identity, and disclose every relaxation of the preferred criteria.

## Default scope

Unless the user specifies otherwise:

- Treat "recent" as a rolling five-year window ending in the current year.
- Target 5–10 papers.
- Include journal articles and reviews only.
- Require JCR Q1 or Q2 in at least one relevant Web of Science category.
- Rank original research above reviews when the user asks for methods, experiments, or engineering evidence.
- Prefer papers whose title, abstract, methods, or validation directly address the requested object and task.

Do not silently replace JCR with CAS partitions, CiteScore quartiles, or SJR quartiles.

## Database priority

Search in this order, adapting to available tools and institutional access:

1. Web of Science or Journal Citation Reports for indexed records and quartile verification.
2. Google Scholar for broad discovery and citation variants.
3. Publisher databases: Elsevier/ScienceDirect, IEEE Xplore, SpringerLink, Wiley Online Library, Taylor & Francis, ACS, Optica, SAGE, and other authoritative publisher sites.
4. Crossref, PubMed, DOAJ, institutional repositories, or discipline-specific indexes for metadata and abstract verification.
5. General web search only after academic sources are insufficient.

When access depends on the user's school subscription or signed-in browser session, use the available browser integration. Never bypass authentication, paywalls, CAPTCHAs, or access controls. Ask the user to sign in when required.

## Search workflow

### 1. Translate the topic into concepts

Identify:

- research object;
- phenomenon or problem;
- method, sensor, algorithm, or system;
- operating environment;
- desired evidence, such as simulation, laboratory test, full-scale test, or flight validation.

Generate English synonyms, abbreviations, spelling variants, and broader/narrower technical terms. Preserve the user's exact phrase as one query, but do not rely on it alone.

### 2. Run the preferred search

Start with:

- publication years within the rolling five-year window;
- article or review document types;
- exact object plus task or method terms;
- likely high-quality journals and publisher databases.

Use Boolean combinations such as:

`(object OR synonym) AND (task OR method) AND (monitoring OR detection OR prediction)`

Avoid issuing a large grid of nearly identical web queries. Use a focused query, inspect results, then refine based on terminology found in relevant records.

### 3. Screen titles and abstracts

For every candidate considered for inclusion:

1. Open the abstract on the publisher or an authoritative index.
2. Confirm the paper studies the requested object or a clearly transferable analogue.
3. Identify the method and measured or predicted variables.
4. Identify the validation level: simulation, coupon test, component test, full-scale test, field/flight test, or operational deployment.
5. Reject papers that only mention the topic in background text.

Classify relevance:

- **Highly relevant:** directly matches the object, task, and operating context.
- **Significantly relevant:** matches the task and method, with a defensible transfer to the requested object.
- **Peripheral:** shares only a material, algorithm, or generic application; exclude by default.

### 4. Verify bibliographic data

Verify:

- original title;
- publication year;
- journal;
- DOI or stable publisher URL;
- article versus conference, thesis, preprint, or report;
- abstract content.

Prefer the final journal version when both a preprint and journal article exist. Deduplicate records by DOI, then by normalized title.

Never invent a DOI, abstract finding, journal metric, or validation claim.

### 5. Verify JCR Q1/Q2

Use the latest available Journal Citation Reports edition unless the user requests the quartile from the publication year.

For each included journal:

- verify JCR status through JCR/Web of Science when accessible;
- record the JCR data year or edition;
- for journals in multiple categories, report the relevant category and quartile when available;
- accept the paper under the default rule if at least one relevant category is Q1 or Q2;
- mark the quartile as "unverified" if authoritative JCR data cannot be accessed.

Publisher metric pages and university-library JCR exports may be used as secondary evidence. Do not present SJR or CAS rankings as JCR.

## Expansion ladder

Expand only when fewer than five highly or significantly relevant papers remain. Change one dimension at a time and state which tier each paper comes from.

1. **Tier A — preferred:** rolling five years, JCR Q1/Q2, direct or significant relevance.
2. **Tier B — broader terminology:** keep the five-year and JCR constraints; broaden synonyms, adjacent platforms, or transferable methods.
3. **Tier C — wider time:** extend to ten years while retaining JCR Q1/Q2.
4. **Tier D — wider publication set:** include other JCR quartiles, ESCI journals, strong peer-reviewed conferences, technical reports, standards, or verified engineering demonstrations.
5. **Tier E — general evidence:** use older or non-indexed sources only when they materially answer the question.

Keep Tier A results first. Label every result outside Tier A and explain why it was retained.

## Output format

Begin with a short scope note containing:

- search date;
- databases searched;
- default or user-specified time window;
- JCR edition used;
- whether the criteria were expanded.

For each selected paper, provide:

**论文题目：** Original title, optionally followed by a Chinese translation  
**年份与期刊：** Year; journal; JCR category/quartile and data year  
**相关性：** Highly relevant or significantly relevant; validation level  
**摘要简介：** 2–3 original sentences summarizing the research problem, method, measured variables, and main finding without copying the abstract  
**论文链接：** Clickable DOI link or stable publisher/database page

Order papers by topic relevance first, then validation strength, recency, and journal quality.

End with:

- a concise statement of gaps or limitations in the retrieved literature;
- any relaxed criteria;
- an offer to export more results or adjust keywords, dates, journals, or evidence types.

## Quality checks

Before returning results, confirm:

- every paper has an abstract-based relevance judgment;
- every year satisfies its declared search tier;
- every Q1/Q2 claim is JCR-based and not inferred from another ranking;
- every link resolves to the stated paper or DOI;
- conference papers, theses, patents, and reports are clearly labeled;
- simulation-only studies are not described as experimental or operational;
- no result is included solely because its title contains the query words.
