# Plan: zyp-vps lint/cerberus alignment

**Status: inventory only, nothing actioned yet.** Findings from a full scan of
`zyp-vps` (2026-07-26), comparing what it actually enforces against what
`zyplux` enforces as the org's reference repo. Each item below is a candidate
to either (a) roll into `zyplux`'s baseline config/docs because it's a
legitimate need the reference repo doesn't yet cover, or (b) flag back to
`zyp-vps` as its own tech debt to fix rather than a baseline gap. Numbers are
stable references — decide item-by-item, check items off as they're resolved.

## 1 ESLint

1. [ ] `@zyplux/no-schemas-outside-contracts` turned off repo-wide in
   `eslint.config.ts` — comment says the contracts-only convention is being
   redesigned, no tracking issue linked.
2. [ ] `unicorn/max-nested-calls` off for `packages/domain-model/src/**`
   (excluding `contracts.ts`) — exempts nested `z.object({ z.object({...}) })`.
3. [ ] `vitest/no-standalone-expect` + `vitest/valid-expect` off for
   `tests/e2e/stories/**/*.test.ts` — works around `@vitest/eslint-plugin`
   1.6.x misparsing a custom "play framework" scene-callback pattern whose
   first destructured fixture is `expect`.
4. [ ] React version pinned to `19.2.7` in the `zyplux()` config call — works
   around `eslint-plugin-react`'s `'detect'` probe crashing under ESLint 10
   flat config.
5. [ ] `react.dom` scoped to specific dashboard/chat-widget globs — avoids
   react-hooks misreading vitest's `test.extend()` `use` parameter as the
   React 19 `use` hook.
6. [ ] `tanstack: true` option exempts TanStack Router `$param`-style
   filenames from the unicorn kebab-case rule.
7. [ ] ~12 scattered inline `eslint-disable-next-line` comments in test
   fixtures/matchers: type-assertion casts onto ambient DOM types, `this`
   binding in vitest custom matchers, one fake-`http://` origin for
   happy-dom, one `any` required by vitest's own `Matchers<T = any>`
   declaration-merging shape, plus the generated `routeTree.gen.ts`.

## 2 TypeScript

1. [x] No `@ts-ignore`/`@ts-expect-error` anywhere — clean. Only suppression
   is `@ts-nocheck` on the auto-generated `routeTree.gen.ts` (standard for
   generated files, not a gap).
2. [x] No relaxed `compilerOptions` or tsconfig `exclude` arrays found vs the
   shared `@zyplux/tsconfig` base — clean.

## 3 Cerberus

1. [ ] `cerberus.toml` carries a "temporary, this-PR-only" overlay comment
   that has persisted 3+ days across multiple commits. Six of the ~7 bites it
   touches are simply `off = true`: `fallow`, `justfile`,
   `story_tests_lockstep_ts`, `vitest`, `lib_ts_test_seam`,
   `fixture_roles_ts`. Only the `knip` bite's `off` has a stated reason
   (custom entry-point allowlist that cerberus has no default for yet).
2. [ ] `jscpd` (duplication) threshold raised three times, most recently to
   `2` — vs `zyplux`'s own flat `0` — each bump labeled "temporarily" with no
   follow-up revert commit or tracking issue.
3. [ ] ability to switch off cerberus bites for certain files, where applicable

## 4 Other linters (ruff / rumdl / knip)

12. [ ] `ruff.toml` disables whole rule families repo-wide: `D` (pydocstyle),
    `DOC` (pydoclint), `CPY001` (copyright header), plus two
    formatter-conflict rules (`COM812`, `ISC001`) — no per-rule justification
    given.
13. [ ] `ruff.toml` per-file-ignores relax `INP001`/`S101` under `tests/**`.
14. [ ] `.rumdl.toml` disables 5 markdown rules repo-wide (`MD013` line-length,
    `MD022`/`MD031`/`MD032` blank-line rules, `MD033` no-inline-html) with no
    reasons given — same 5 rules `zyplux` itself already disables, so likely
    just needs the same justification, if any exists, ported over.
15. [ ] `.rumdl.toml` excludes `.agents/skills/**` (vendored, not hand-edited —
    reasonable) and relaxes `MD024` to siblings-only (matches `zyplux`'s own
    setting).
16. [ ] `knip.prod.json` (the stricter prod-export-surface pass) exists and
    runs via `just knip` locally, but is **not run in CI** — silent gap
    between local and CI enforcement. Related work already tracked in
    [[knip-and-export-discipline]].

## 5 Smoke-test workarounds

Checks that belong in lint/cerberus config but are implemented as hand-rolled
vitest smoke tests instead:

17. [ ] `tests/smoke/stories/type-surface.test.ts` — AST-derived check that
    type-only imports come only from a package's `types.ts` or
    `@zyplux/domain-model`, via a custom fixture loader
    (`tests/smoke/fixtures/act.ts`). Candidate for a custom eslint rule or
    cerberus bite instead of a runtime test.
18. [ ] `tests/smoke/stories/tree-shaking.test.ts` — two more hand-rolled
    invariants: no wrangler config outside an allowlist enables
    `nodejs_compat`, and every package declares `sideEffects: false`. Both
    maintain manual allowlists in code (`NODEJS_COMPAT_ALLOWLIST`,
    `SIDE_EFFECTS_ALLOWLIST`) that would normally live as a config exclude
    list.

## 6 Docs/README mismatches

19. [ ] `README.md` describes the quality gate as
    install → knip → typecheck → lint → test, omitting the `cerberus` step
    that the justfile and CI both actually run.
20. [ ] `CLAUDE.md` documents the `knip`/cerberus linkage and two unrelated
    pinned-dependency workarounds, but says nothing about the other 5 disabled
    cerberus bites or the `jscpd` threshold history above.

## 7 Justfile / CI parity gaps

21. [ ] `just test` deliberately skips `pytest` (comment: "Python tests and cz
    are deliberately unwired for now") — only CI runs pytest directly, so
    local `just check` can't catch a Python regression before push.
22. [ ] CI's `knip` step runs only `bun run knip`, not the stricter
    `knip.prod.json` pass that `just knip` runs locally (same gap as above,
    from the CI side).
23. [ ] CI never runs `bun run lint:mermaid`, though it's part of the local
    `just lint`/`just check` chain.
