---
name: download-campus-literature
description: Batch-download legally accessible scholarly PDFs from DOI lists, numbered references, OpenAlex links, or bibliography text using open-access sources and the user's active campus subscription. Use for bulk literature acquisition, publisher-specific download routing, PDF validation, resume manifests, CAPTCHA/access-error triage, document-delivery routing, and low-token script-first workflows across ScienceDirect/Elsevier, MDPI, IEEE, Springer Nature, Wiley, Taylor & Francis, ACS, Frontiers, SEG/GeoScienceWorld, repositories, and similar scholarly platforms.
---

# Campus literature download

Use deterministic scripts first. Escalate only the unresolved publisher groups to a browser.

## Boundaries

- Download only open-access copies, repository copies, or full text authorized by the user's current institutional subscription.
- Never bypass a paywall, CAPTCHA, login, rate limit, publisher block, or technical access control.
- Do not query, search, or download from Sci-Hub or other unauthorized shadow libraries. Use open repositories, author manuscripts, institutional subscriptions, or library document delivery instead.
- Do not export browser cookies, tokens, signed PDF URLs, local storage, or credentials into scripts.
- Treat HTTP 401/403/429, repeated CAPTCHA, `IP blocked`, and publisher security interstitials as stop or browser-review states.
- Ask for explicit permission before solving each CAPTCHA, as required by the active browser-control instructions.

## Cost and token policy

1. Run `scripts/batch_download.py` over the entire input before opening a browser.
2. Read only the printed summary and failed rows from `browser_queue.csv`; do not inspect every successful item.
3. Group failures by publisher and status. Reuse one authenticated browser session per publisher.
4. If collaboration tools are available and the user asked to minimize model cost, delegate bounded DOI normalization, manifest triage, or repetitive known-button browser work to `gpt-5.6-terra` at low or medium reasoning. Do not run parallel agents against the same Chrome profile.
5. Keep CAPTCHA, login ambiguity, native PDF-viewer failures, publisher blocks, and novel page layouts in the main session.
6. Do not browse for a paper already marked `downloaded`, `already_downloaded`, or `document_delivery_requested`.

## Script-first workflow

Run:

```powershell
python scripts/batch_download.py references.txt `
  --download `
  --output-dir downloaded_papers `
  --manifest download_manifest.csv `
  --email YOUR_UNPAYWALL_EMAIL
```

The email is sent only to Unpaywall. Omit `--email` to skip Unpaywall and use OpenAlex plus publisher/repository metadata.

The script:

- extracts and deduplicates DOI values;
- queries OpenAlex and optionally Unpaywall;
- checks conservative publisher/repository PDF metadata;
- downloads only responses that validate as PDF;
- resumes from existing valid files;
- records every result in `download_manifest.csv`;
- writes browser-only failures to `browser_queue.csv`;
- stops safely on rate limiting.

Use scan-only mode by omitting `--download`. Use `--only-publisher Elsevier` or `--max-items N` for a bounded retry.

## Browser escalation

Read [references/publisher-playbook.md](references/publisher-playbook.md) only for publishers present in `browser_queue.csv`.

For each publisher group:

1. Select the user's explicitly requested browser; otherwise use the browser chosen by its skill.
2. Verify the page visibly recognizes institutional or open access.
3. Open or click the normal `PDF`, `View PDF`, or `Download PDF` control once.
4. If a CAPTCHA appears, pause and obtain explicit user permission before solving it.
5. Prefer a browser setting that directly downloads PDFs. If a PDF extension reports “未能加载 PDF 文档”, choose “在 Chrome 的 PDF 查看器中打开” or let the user perform that native-interface click.
6. Inspect the download folder by recent modification time. Never infer success from a new tab alone.
7. For several browser-downloaded files, run the deterministic reconciliation command below instead of matching and renaming them manually.
8. Finalize browser tabs according to the browser skill.

```powershell
python scripts/reconcile_downloads.py browser_queue.csv `
  --downloads "$env:USERPROFILE\Downloads" `
  --output-dir downloaded_papers `
  --manifest download_manifest.csv `
  --recent-minutes 120 `
  --apply
```

Do not repeatedly request expiring signed asset URLs. Return to the article page and use its visible PDF control to obtain a fresh authorized download.

## Document delivery

For Wuhan University of Technology document delivery through `https://spis.hnlat.com/`, read [references/spis-document-delivery.md](references/spis-document-delivery.md).

Use document delivery after legal OA/repository searches fail and campus access is unavailable or blocked by a manual security check. Obtain action-time user confirmation before accepting the service terms and submitting each batch of requests. After submission, record `document_delivery_requested` and do not submit duplicates.

When a delivered paper arrives by QQ Mail, follow the verified email-to-PDF procedure in the reference. Keep browser work limited to the visible `点击下载` / `继续访问` / `下载全文` controls; perform file discovery, renaming, validation, and manifest updates with scripts or the shell.

## Verification

Accept a file only when all checks pass:

- starts with `%PDF-`;
- is larger than 10 KB;
- is not HTML renamed as `.pdf`;
- opens with `pypdf` when available;
- has a plausible page count.

Use `scripts/verify_pdfs.py OUTPUT_DIR` after browser downloads. Report counts, failures, and output paths; do not dump signed URLs or verbose browser traces.

## Failure states

- `needs_browser_captcha`: use browser flow after user permission.
- `needs_browser_access`: verify campus access or ask the user to sign in.
- `needs_browser`: normal script path did not expose a downloadable PDF.
- `needs_manual_security_check`: the official page shows Cloudflare, “Just a moment…”, or another security interstitial. Stop automation and let the user complete the normal browser check manually; do not probe alternate PDF endpoints.
- `needs_document_delivery`: the publisher recognizes the institution but explicitly says the institution does not provide access. Stop browser retries and route to the university library's 文献传递/馆际互借 service or an author-copy request.
- `document_delivery_requested`: the official document-delivery platform accepted the request. Record the platform and request date, do not retry, and wait for delivery by the platform or email.
- `rate_limited`: stop the domain; retry later with a longer delay.
- `invalid_pdf`: downloaded content was HTML or malformed; route to browser.
- `request_error`: retry once only if transient, then queue for review.
