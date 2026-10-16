# Selective model retry implementation plan

> Execute inline with superpowers:executing-plans. User explicitly requests continuous completion while AFK; no intermediate approval pauses.

**Goal:** Retry selected failed segments with user-selected stage models while preserving successful results, and open source media only after complete export.

**Architecture:** Keep checkpoint identity and split_plan stable. Store per-stage provenance, error records and latest processing settings as optional schema-1 fields. Use a configured Gemini adapter and shared translation cache helper.

**Tech Stack:** Python, Tkinter, google-genai, httpx, pytest.

**Spec:** ../specs/2026-10-14-selective-model-retry-design.md

## Global constraints

- No automatic fallback, no audio uploads in tests, no secret/response text in errors.
- Preserve source identity, language and split plan; keep successful SRT/transcripts.
- Legacy checkpoint compatibility; normal temporary-file cleanup remains intact.
- Keep existing dirty ten-minute changes; no commit/push of product code without request.

## Review focus

- Restart after switching service must load original checkpoint and latest preferences.
- Translation batches from another model must never be reused.
- Source selection changes must not alter the completed-media button target.
- Quota stop must retain unprocessed failed indices in retry UI.
- Safety blocked outputs must be clearly identified, not silently retried on another model.

## Task 1: Stage-configured models and durable caches

Files: src/model_config.py (new), src/translator.py, src/groq_provider.py, src/resume.py;
tests/test_selective_models.py (new).

Interfaces: processing_settings(client) -> dict; translation_cache(state,index,model) -> dict;
GeminiProvider.transcribe_saved()/translate() matches GroqProvider protocol.

- [ ] Write regression tests that process segment 0 with a new provider and leave segment 1's saved SRT untouched; verify original checkpoint identity after reload.
- [ ] Run `python -m pytest tests/test_selective_models.py -q -p no:cacheprovider`; expect missing model_config functions.
- [ ] Implement configured adapters; namespace raw ASR cache by provider identity and translation cache by model; retain old caches under original model.
- [ ] Capture provenance only after successful stage persistence; persist latest settings separately from work identity.
- [x] Run focused suite, expect all green. First full run: 166 passed.

## Task 2: Safe errors and selected retry UI

Files: src/errors.py (new), src/gui.py, src/locales/{zh_tw,zh_cn,en,ja}.py.
Interfaces: classify_error(exc) -> controlled code; UI builds client from processing selection;
retry updates client but not checkpoint identity/split plan.

- [ ] Write tests for JSON malformed/truncated/blocked, HTTP status and simulated secret redaction.
- [ ] Write GUI tests for selected-only retry with new model; block changes while busy, fixed source language on retry, and errors retained across restart.
- [ ] Run focused tests, expect missing error reasons/retry model behavior.
- [ ] Add separate translation selector; rebuild client before retry after credential/source validation; preserve completed segments and transcription results.
- [ ] Save structured failures; show localized reasons/stage/models in failed rows; keep unknown reasons honest.
- [x] Run focused tests and full suite; expect green. 176 passed, then 183 with restart/error/provenance cases.

## Task 3: Completed source action and verification

Files: src/gui.py, localized strings, README.md, docs/ARCHITECTURE.md, docs/CHANGELOG.md.

- [ ] Write tests that only complete success enables source action, uses completed source even after file selection changes, and handles open/missing-file errors.
- [ ] Run focused tests; expect missing source action.
- [ ] Add hidden button controlled by completed work snapshot; invoke os.startfile only on click; clear on new work and failed/stopped completion.
- [ ] Run full suite and git diff --check; review cross-service restart, cache selection, quota and legacy migration paths.
- [ ] Update user docs with limits: Gemini ASR has one supported model, translation alternatives depend on account availability, no live quota guarantee.

## Execution record

Ruling: execute in the current shared checkout, retaining dirty changes, because the user asked to finish this project in-place while AFK; do not create a separate checkout invisible to their launcher.
Ruling: do not create product commits or push; earlier git requests were scoped to earlier changes.

Pre-flight: task 2 consumes task 1's configured provider protocol and processing_settings; signatures agree. Task 3 consumes task 2's done messages, preserving the existing tuple contract.
Task 1: complete; model cache/provenance tests RED→GREEN, full suite 166 passed.
Task 2: complete; GUI selected retry/quota/restart/security tests RED→GREEN, suite 183 passed.
Task 3: complete; source-open tests RED→GREEN, independent whole-change review completed.
Ruling: use Gemini 3.6 Flash as alternative translation model, not deprecated 3.5 Flash; official model documentation now routes 3.5 to 3.6. Account access and quota are not guaranteed.

Final review: independent read-only reviewer checked current tree; no Critical issues.
Final: fixed persisted-state/export mismatch and partial retry false success; test_retry_subset_after_restart_does_not_discard_other_pending_progress RED→GREEN, stop-saved export test added; suite 185 passed.
Final: fixed one-shot history locator not being consumed; regression RED→GREEN, final suite 187 passed.
Final: timestamp classifications originally graded minor regraded Important for this task's informative-error requirement; regression RED→GREEN, final suite 187 passed.
Ruling: live model account access/quota and player association are not verified using user resources — unit/integration tests use controlled local responses — availability or player setup may still require user action.
Ruling: unknown Gemini Interactions safety representations remain classified only when documented/controlled evidence is present; missing annotations alone are not falsely labelled content blocks.

Final verification: `python -m pytest -q -p no:cacheprovider` → 187 passed in 6.36s; no external API requests. Product changes remain uncommitted, as requested workflow did not include commit/push.
