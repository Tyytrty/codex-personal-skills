# Publisher playbook

Load only the section needed for publishers in `browser_queue.csv`.

## Shared rules

- Work from the DOI landing page or article page.
- Confirm visible open-access or institutional-access entitlement before downloading.
- Batch by publisher so the same authenticated session and page pattern are reused.
- Use one normal click per paper. Stop on 429, repeated CAPTCHA, `IP blocked`, or an access-security interstitial.
- Signed PDF asset URLs are short-lived and session-bound. Do not copy them to external HTTP clients or store them in reports.
- A file named `.pdf` is not proof of success. Validate its header and page structure.

## Elsevier / ScienceDirect

Signals: DOI prefix `10.1016`, host `sciencedirect.com`, PDF endpoint containing `pdfft`.

Script path:

1. Prefer a legal OpenAlex/Unpaywall repository copy.
2. Otherwise inspect the DOI landing page for PDF metadata.
3. Route challenge HTML and subscription-only results to Chrome.

Browser path:

1. Open the article page and verify the institutional-access badge.
2. Click `View PDF`.
3. If Cloudflare shows a CAPTCHA, ask the user for permission for that CAPTCHA, then solve it through the visible browser UI.
4. With Chrome configured to download PDFs, `View PDF` should create `1-s2.0-...-main.pdf`.
5. If a PDF extension says it cannot load the document, choose `在 Chrome 的 PDF 查看器中打开`; native extension overlays may require the user to click.
6. If `pdfft.htm` or similar is downloaded, it is challenge HTML, not the paper. Return to the article page rather than retrying that file.

Common problems:

- `CPE00001` or `IP blocked`: stop; do not retry the direct endpoint.
- A blank/dark PDF tab: inspect Downloads before assuming failure.
- Direct requests to the signed `pdf.sciencedirectassets.com` URL may return 403 because the URL is short-lived and bound to the browser session.

## MDPI

Signals: DOI prefix `10.3390`, host `mdpi.com`.

- Prefer OpenAlex/Unpaywall or the page's `citation_pdf_url`.
- The DOI-suffix `/pdf` route often resolves to the article PDF.
- HTML or 403 responses should be routed to the normal article `Download PDF` button.
- MDPI articles are commonly open access, but still respect rate limits and validate every response.

## IEEE Xplore

Signals: DOI prefix `10.1109`, host `ieeexplore.ieee.org`.

- Prefer an open repository copy when available.
- On campus access, open the IEEE record and use its visible `PDF` control.
- Do not synthesize or loop through `stampPDF`/`getPDF` URL variants.
- A login/subscribe prompt means the current session is not entitled; do not bypass it.

## SpringerLink / Nature

Signals: DOI prefixes `10.1007` or `10.1038`; hosts `link.springer.com` or `nature.com`.

- Prefer `citation_pdf_url`, OpenAlex, Unpaywall, or a repository copy.
- Use the article's visible `Download PDF` control for subscribed content.
- Check whether the result is an article PDF rather than a book chapter preview or supplementary file.

## Wiley

Signals: common prefixes `10.1002` and `10.1111`, host `onlinelibrary.wiley.com`.

- Prefer repository/OA metadata.
- Use `PDF` or `Download PDF` in the authenticated browser.
- Wiley may redirect through identity or consent screens; handle only visible normal navigation and stop on access denial.
- If the page recognizes the user's institution but says it “does not provide access to this content”, record `needs_document_delivery`. Do not repeat the PDF click or try alternate Wiley PDF URLs.
- For `10.1111/1365-2478.12303`, Wuhan University of Technology is recognized but does not provide access; route directly to 文献传递/馆际互借 or an author-copy request after one current-state verification.

## SEG / GeoScienceWorld

Signals: DOI prefix `10.1190`; hosts `pubs.geoscienceworld.org`, `library.seg.org`, or an SEG DOI landing page.

- Prefer OpenAlex, Unpaywall, author repositories, and institutional repositories before opening the publisher page.
- Use the normal article `PDF` control only after visible institutional entitlement is confirmed.
- If the article opens a Cloudflare or “Just a moment…” security page, record `needs_manual_security_check` and stop automation. Let the user complete the normal check manually; do not synthesize PDF URLs, alter request headers, or loop through endpoints.
- For `10.1190/geo2020-0170.1`, use the manual-security-check route after repository searches return no legal full text.

## Taylor & Francis

Signals: prefix `10.1080`, host `tandfonline.com`.

- Prefer repository copies.
- Use the normal article PDF button under institutional access.
- Do not automate repeated retries after bot or rate-limit pages.

## ACS

Signals: prefix `10.1021`, host `pubs.acs.org`.

- Prefer accepted manuscripts in repositories.
- Use the authenticated article `PDF` button once.
- Stop on bot detection, access denial, or account prompts.

## Frontiers and other open-access publishers

Signals: prefix `10.3389` for Frontiers.

- Prefer OpenAlex/Unpaywall and page PDF metadata.
- Follow the publisher's stable PDF link only when exposed by metadata or the visible page.
- Validate because some endpoints return HTML consent or error pages with HTTP 200.

## Institutional repositories

- Accept publisher PDFs or author-accepted manuscripts when the repository legally exposes them.
- Preserve version information in the manifest note, for example `accepted_manuscript`.
- Prefer a stable repository URL over an expiring publisher asset URL.

## Legal fallback order

1. Check OpenAlex, Unpaywall, NVA, institutional repositories, and author-accepted manuscripts.
2. Check the active campus subscription once through the normal publisher interface.
3. On `needs_manual_security_check`, hand the official page to the user for normal manual verification or offer the university's official SPIS document-delivery route.
4. On `needs_document_delivery`, stop publisher retries and prepare the DOI, title, journal, year, volume, issue, and pages for the official SPIS document-delivery route described in `references/spis-document-delivery.md`.
5. Do not use Sci-Hub or other unauthorized shadow libraries.
