# Plan: replace Bun with Node 26 + pnpm

**Status: inventory only, nothing actioned yet.** Every change needed to move this repo off Bun onto Node 26 (runtime) and pnpm (package manager, chosen over npm because npm has no `catalog:` protocol). Numbers are stable references — check items off as they're resolved.

Node 26 refuses to type-strip files under `node_modules`, so the published packages must ship compiled JS. That is the one irreversible consequence of this migration and it drives items 34–48.

`zyp-vps` already runs Node 26.5 + pnpm 11 with nine cerberus bites switched off in its `cerberus.toml`; items 93–121 are what let it switch them back on.

## 1 Runtime APIs

1. [ ] `packages/util-ts/src/shell.ts` — replace all ~40 `Bun.$` call sites with a `node:child_process` harness.
2. [ ] `packages/util-ts/src/shell.ts` — reimplement `.quiet()`, `.nothrow()`, `.cwd()`, `.env()`, `.text()` chaining on the new harness.
3. [ ] `packages/util-ts/src/shell.ts` — reimplement the tagged-template argument escaping `Bun.$` provides.
4. [ ] `packages/util-ts/src/shell.ts:105` — `$`'s direct-call passthrough currently types off `Parameters<typeof Bun.$>`; retype against the new harness.
5. [ ] `packages/util-ts/src/shell.ts:108` — `captureMerged` relies on `2>&1` inside the template; needs explicit shell or stream-merging.
6. [ ] `packages/util-ts/src/shell.ts` — extract the exec primitive into its own module so tests can `vi.mock` it instead of reassigning a global.
7. [ ] `packages/util-ts/src/json.ts:11` — `Bun.file(path).json()` → `node:fs/promises` read + parse.
8. [ ] `packages/util-ts/src/poll.ts:9` — `Bun.sleep` → `node:timers/promises`.
9. [ ] `packages/util-ts/src/toml.ts:5` — `Bun.TOML.parse` → `smol-toml` (Node has no TOML parser).
10. [ ] Add `smol-toml` to the catalog and to `packages/util-ts` dependencies; decide dependency vs peer, since `@zyplux/util` is published.
11. [ ] Confirm `smol-toml` preserves the syntax-error/schema-error distinction locked in by `tests/util-ts/stories/4-toml.test.ts`.
12. [ ] `apps/cz/src/deps-catalog.ts:30` — `Bun.file(file).text()` → `node:fs/promises`.
13. [ ] `apps/cz/src/commands/deps-catalog.ts:38` — `Bun.write` → `node:fs/promises`.
14. [ ] `apps/cz/src/commands/publish-tagged-target.ts:24` — `bun pm pack && bunx npm@11 publish` → `pnpm pack && npm publish`.
15. [ ] `apps/cz/src/commands/test.ts:73,78` — `['bun', 'run', 'test']` → `['pnpm', 'run', 'test']`.
16. [ ] `apps/cz/src/commands/test.ts:113` — brief text names `bun run test`.
17. [ ] `apps/cz/src/index.ts:1` — `#!/usr/bin/env bun` → `node`.

## 2 Module resolution and TypeScript config

18. [ ] Add explicit `.ts` extensions to 112 extensionless relative imports across `apps/cz/src`, `packages/*/src`, `packages/eslint-config/scripts`, `tests/*/src`, `tests/*/fixtures`, `tests/*/stories`.
19. [ ] `packages/tsconfig/base.json` — `moduleResolution: "bundler"` → `"nodenext"`.
20. [ ] `packages/tsconfig/base.json` — `module: "Preserve"` → `"nodenext"`.
21. [ ] `packages/tsconfig/base.json` — add `allowImportingTsExtensions`.
22. [ ] `packages/tsconfig/base.json` — add `rewriteRelativeImportExtensions` (needed once packages emit JS).
23. [ ] `packages/tsconfig/base.json` — `emitDeclarationOnly: true` → full emit for published packages.
24. [ ] `packages/tsconfig/base.json` — keep `erasableSyntaxOnly: true`; it is already what makes the source Node-strippable.
25. [ ] `packages/tsconfig/bun.json` — replace with a `node.json` preset carrying `types: ["node"]`.
26. [ ] `packages/tsconfig/bun.json` — decide whether to keep it as a deprecated alias; five sibling repos extend it, so removal is a breaking change.
27. [ ] `packages/tsconfig/tui.json:7` — `types: ["bun", "react"]` → `["node", "react"]`.
28. [ ] `packages/tsconfig/web.json:8` — `types: ["bun", "react", "react-dom"]` → `["node", ...]`.
29. [ ] `packages/tsconfig/package.json` — `files` list and version bump for the preset rename.
30. [ ] `tsconfig.tooling.json:2` — extends `@zyplux/tsconfig/bun.json`.
31. [ ] `packages/util-ts/tsconfig.json:2` — extends `@zyplux/tsconfig/bun.json`.
32. [ ] `packages/eslint-config/tsconfig.json:2` — extends `@zyplux/tsconfig/bun.json`.
33. [ ] `apps/cz/tsconfig.json` and `tests/*/tsconfig.json` — same preset swap.

## 3 Publishing (packages must ship compiled JS)

34. [ ] Add a build step producing `.js` + `.d.ts` for `packages/util-ts`.
35. [ ] Add a build step for `packages/eslint-config`.
36. [ ] Add a build step for `apps/cz`.
37. [ ] Add a build step for `tests/fixtures` (`@zyplux/tests-fixtures` is a published release target).
38. [ ] `packages/util-ts/package.json` — `exports` from `./src/*.ts` to built output.
39. [ ] `packages/eslint-config/package.json` — `exports` from `./src/*.ts` to built output.
40. [ ] `apps/cz/package.json` — `exports` and `bin` from `./src/index.ts` to built output.
41. [ ] `tests/fixtures/package.json` — `exports` from `./src/index.ts` to built output.
42. [ ] All four — `files` must include the build output, not (only) `src`.
43. [ ] All four — verify the `#`-subpath `imports` maps still resolve post-build.
44. [ ] Add `prepack` (or equivalent) so packing cannot publish stale output.
45. [ ] `release-targets.toml` — `surface` globs for the four packages must cover build inputs, not output.
46. [ ] Verify `pnpm pack` tarball contents for each package before the first real publish.
47. [ ] Version-bump all four packages; the published shape changes even where the API does not.
48. [ ] Decide whether `@zyplux/tsconfig` needs a bump (JSON-only, but the preset set changes).

## 4 Package manager and lockfile

49. [ ] Delete `bun.lock`, generate `pnpm-lock.yaml`.
50. [ ] Create `pnpm-workspace.yaml`; move the `packages/*`, `apps/*`, `tests/*` globs out of `package.json`.
51. [ ] Move the 24-entry `catalog` out of `package.json` into `pnpm-workspace.yaml`.
52. [ ] Verify every `catalog:` and `workspace:*` specifier still resolves under pnpm.
53. [ ] `package.json` — `engines.bun` → `engines.node` (`>=26`).
54. [ ] `package.json` — `packageManager: "bun@1.3.14"` → pnpm.
55. [ ] Add an explicit pnpm bootstrap step; Corepack is no longer distributed with Node as of v25.
56. [ ] Add `.nvmrc` (or `.node-version`) pinning the Node version.
57. [ ] Add `.npmrc` if pnpm hoisting/linking defaults need adjusting for this workspace.
58. [ ] Drop `@types/bun` from the catalog; add `@types/node`.
59. [ ] Drop `@types/bun` from all 8 manifests that declare it: root, `apps/cz`, `packages/util-ts`, `packages/eslint-config`, `tests/cz`, `tests/eslint-config`, `tests/fixtures`, `tests/util-ts`.
60. [ ] Verify `npm-check-updates` still drives upgrades correctly against a pnpm catalog.

## 5 Scripts and justfile

61. [ ] `package.json:46` — `lint:fix` invokes `bun run lint`.
62. [ ] `package.json:49` — `cz` script invokes `bun apps/cz/src/index.ts`.
63. [ ] `packages/eslint-config/package.json:49` — `dump-rules` invokes `bun run scripts/dump-rules.ts`.
64. [ ] `justfile:21` — `bun install`.
65. [ ] `justfile:26,27` — `bun run knip` (both passes).
66. [ ] `justfile:32` — `bun run typecheck`.
67. [ ] `justfile:37,38` — `bun run lint:fix`, `bun run format`.
68. [ ] `justfile:46` — `bun run cz test`.
69. [ ] `justfile:57,64,65` — upgrade recipes.
70. [ ] `justfile:72` — `bun run cz push-branch`.
71. [ ] `justfile:79` — `bun run cz clean`.
72. [ ] `justfile:87` — `bun run cz clone-reference-repo`.
73. [ ] `justfile:91` — `bun run --cwd packages/eslint-config dump-rules`.
74. [ ] `justfile:99` — `bun run --silent cz release-bumped-targets`.
75. [ ] Add a `build` recipe and wire it into `check` ahead of `test`.
76. [ ] Items 64–74 land in the `# BASELINE` region — edit `apps/cerberus/src/cerberus/baseline.just`, never the justfile.

## 6 CI and container image

77. [ ] `containers/ci/Containerfile:1` — `FROM oven/bun:1.3.14-debian` → a Node 26 base.
78. [ ] `containers/ci/Containerfile:4` — image description says "bun + uv + git, no Node".
79. [ ] `containers/ci/Containerfile` — install pnpm in the image.
80. [ ] `containers/ci/Containerfile:5` — bump `org.opencontainers.image.version`; publish a new GHCR tag.
81. [ ] `.github/workflows/ci.yml` — `bun install --frozen-lockfile`.
82. [ ] `.github/workflows/ci.yml` — `bun run knip` / `typecheck` / `lint` / `test` steps.
83. [ ] `.github/workflows/ci.yml` — `bunx prettier --check .`.
84. [ ] `.github/workflows/ci.yml` — pin the new CI image tag.
85. [ ] `.github/workflows/ci.yml` — add a build step before `test`.
86. [ ] `.github/workflows/bootstrap-npm.yml` — `oven-sh/setup-bun` → `actions/setup-node`.
87. [ ] `.github/workflows/bootstrap-npm.yml` — `bun install --frozen-lockfile`, `bun run cz`.
88. [ ] `.github/workflows/release.yml` — `oven-sh/setup-bun` in all four jobs (`resolve`, `npm`, `pypi`, `ghcr`).
89. [ ] `.github/workflows/release.yml` — `bun install --frozen-lockfile` in all four jobs.
90. [ ] `.github/workflows/release.yml` — `bun run cz` invocations in all four jobs.
91. [ ] `.github/workflows/release.yml` — publish jobs must build before packing.
92. [ ] Add pnpm-store caching to CI.

## 7 Cerberus (org gate — must accept both toolchains, not swap to Node-only)

93. [ ] `cerberus.toml` `[ci_check_sequence.required].ts` — the six literal `bun …` commands must become package-manager-aware.
94. [ ] `bites/ci_check_sequence_bite.py:91` — container requirement and its "Node-free guarantee" message.
95. [ ] `cerberus.toml` `[workflow_toolchain_only].allowed_setup_actions` — add `actions/setup-node`.
96. [ ] `bites/workflow_toolchain_only_bite.py:30` — the `pnpm|yarn … global` regex blocks the standard pnpm bootstrap.
97. [ ] `bites/workflow_toolchain_only_bite.py:50` — failure message says "the toolchain is uv + bun".
98. [ ] `workspaces.py:19` — `bun_member_globs` reads `package.json` `workspaces`; under pnpm membership lives in `pnpm-workspace.yaml`.
99. [ ] `workspaces.py` — rename the function once it is no longer Bun-specific.
100. [ ] `bites/zyplux_deps_latest_bite.py:82` — reads `bun.lock`.
101. [ ] `bites/zyplux_deps_latest_bite.py:57` — `_npm_usages` regex parses bun.lock format; pnpm-lock.yaml differs.
102. [ ] `bites/catalog_pinned_deps_bite.py` — reads the catalog from `package.json`.
103. [ ] `bites/story_docs.py:234` — bun workspace member dirs.
104. [ ] `bites/test_seam.py:85` — bun workspace member dirs.
105. [ ] `bites/jscpd_bite.py:47` — `bun_member_globs` call.
106. [ ] `bites/jscpd_bite.py:54` — `bunx` subprocess invocation.
107. [ ] `bites/fallow_bite.py:267` — `bunx` subprocess invocation.
108. [ ] `bites/fallow_bite.py:201,225` — `bunx` rerun hints in failure messages.
109. [ ] `bites/fallow_bite.py:20` — module docstring describes the `bunx` pipe chain.
110. [ ] `bites/justfile_bite.py:36` — `_CZ_CLEAN_INVOCATIONS` accepts only `cz` / `bun run cz` / `bunx cz`.
111. [ ] `bites/justfile_bite.py:91,252` — managed tools must run via `uv run`/`bunx`.
112. [ ] `bites/justfile_bite.py:79` — docstring lists the accepted invocations.
113. [ ] `bites/vitest_bite.py:23,24,41,64,72,82` — the `bun:test` / `bun test` bans go vestigial; keep or generalize deliberately.
114. [ ] `tool_pins.py:1` — docstring says the tools run via `bunx`.
115. [ ] `baseline.just:18,20,25,26,29,31,36,37,45,56,63,64,71,78` — every `bun` invocation.
116. [ ] `baseline.just` — add the `build` recipe from item 75.
117. [ ] `cerberus.toml` `[knip].allowed_customizations` — check whether pnpm changes the required `ignoreBinaries`.
118. [ ] Confirm the `wrapped_tools` list still holds when tools run via `pnpm exec` rather than `bunx`.
119. [ ] Bump `apps/cerberus/pyproject.toml` version and cut a release.
120. [ ] Verify the five Bun sibling repos still pass on the released cerberus before merging.
121. [ ] Re-enable `[ci_check_sequence]` and `[workflow_toolchain_only]` in `zyp-vps/cerberus.toml`.

## 8 Tests and fixtures

122. [ ] `tests/fixtures/src/shell.ts:113,133,134,136` — the fake reassigns `Bun.$`; move to mocking the exec module from item 6.
123. [ ] `tests/fixtures/src/shell.ts:8,9` — `ShellPromise` / `ShellValue` types derive from `Bun.$`.
124. [ ] `tests/fixtures/src/story.ts:72,73,77` — stubs `Bun.sleep`; switch to fake timers or injection.
125. [ ] `tests/fixtures/package.json` — description and `bun` keyword.
126. [ ] `tests/util-ts/stories/6-shell.test.ts:112` — story name references `Bun.$`.
127. [ ] `tests/cz/stories/5-bootstrap-npm-target.test.ts:32,43,47` — asserts on `bun pm pack` / `bunx npm@11`.
128. [ ] `tests/cz/stories/8-publish-tagged-target.test.ts:20,27,31,32` — same assertions.
129. [ ] `tests/cz/stories/12-parallel-workspace-tests.test.ts` — nine `bun run test` assertions.
130. [ ] `tests/cz/stories/13-smart-js-test-filter.test.ts:67,71,77,111,115` — `bun run test` assertions.
131. [ ] `tests/util-ts/stories/1-manifest.test.ts:8` — fixture manifest contains `"build": "bun build"`.
132. [ ] Verify `vitest.config.ts` `isolate: false` still behaves under Node.
133. [ ] Verify istanbul coverage still resolves `src` paths once packages emit to a build directory.
134. [ ] Verify `apps/cz/src/commands/test.ts`'s programmatic `createVitest` filtering still works under Node.

## 9 Docs and comments

135. [ ] `README.md:20` — `@zyplux/util` described as "Bun utilities".
136. [ ] `README.md:29` — "Dual workspace: bun (TS) + uv".
137. [ ] `CLAUDE.md:9` — gate described as spanning "the bun (JS/TS) and uv" workspaces.
138. [ ] `CLAUDE.md:11` — `bun run test` regenerates coverage.
139. [ ] `packages/util-ts/README.md:3` — "Small Bun utilities … consumed directly under Bun".
140. [ ] `packages/util-ts/README.md:8` — `bun add` install line.
141. [ ] `packages/util-ts/README.md:36` — `Bun.file` in the `readJson` description.
142. [ ] `packages/util-ts/README.md:45` — `$` documented as `Bun.$` augmented.
143. [ ] `packages/util-ts/README.md:47` — manifest schema described as reading "bun `workspaces`/`catalog`".
144. [ ] `packages/util-ts/package.json` — description and `bun` keyword.
145. [ ] `packages/eslint-config/README.md:3` — "consumed directly under Bun".
146. [ ] `packages/eslint-config/README.md:8` — `bun add -D` install line.
147. [ ] `packages/tsconfig/README.md:10,17` — `bun.json` preset row and example.
148. [ ] `apps/cz/package.json` — `bun` keyword.
149. [ ] `docs/guide/publish.md:36,39,40` — `bunx npm@11` login/trust instructions.
150. [ ] `.gitignore:1` — "# JavaScript / bun" comment.
151. [ ] `ruff.toml:17` — S607 comment lists `bun` as tooling invoked off PATH.
152. [ ] `packages/eslint-config/src/rules/type-aware/no-unvalidated-json.ts:64` — rule description cites `Bun.file` as a boundary example.
153. [ ] `docs/roadmap/knip-and-export-discipline.md:51,94` — Bun bundler and bundler-mode resolution notes.

## 10 Machine setup (reproducibility)

154. [ ] `apps/totchef/examples/totchef_recipe.toml:160` — `[url.bun]` installs Bun; add a Node install path.
155. [ ] `apps/totchef/examples/totchef_recipe.toml:164` — `[bun]` section installs `@zyplux/cz` globally; needs a pnpm equivalent.
156. [ ] `apps/totchef` — add a node/pnpm cook alongside `bun_cook`.
157. [ ] Out of scope, do not remove: `apps/totchef`'s `[bun]` cook and `skills_cook`'s `bunx` usage are product features configuring user machines, not repo infrastructure.

## 11 Node 26 features worth adopting

158. [ ] Enable the portable compile cache for `cz` to recover part of Bun's startup advantage.
159. [ ] Cache the compile-cache directory in CI.
160. [ ] Consider a cerberus bite asserting CI-invoked tooling runs under Node's permission model (`--permission`, `--allow-*`); Bun has no equivalent.
161. [ ] Not applicable, checked: `Temporal` (no `Date` usage anywhere in `apps/`, `packages/`, `tests/`), `Map.getOrInsertComputed()` (existing `Map`/`Set` usage is membership testing, not memoization), `Iterator.concat()`, `crypto.randomUUIDv7()`, undici 8, `req.signal`.

## 12 Verification

162. [ ] `just c` passes clean.
163. [ ] `bunx`-free: no `bun` or `bunx` string remains outside `apps/totchef` and this document.
164. [ ] Install a packed tarball of each published package into a scratch Node project and run it.
165. [ ] Install the same tarballs into a scratch Bun project; the five Bun sibling repos must keep working.
166. [ ] Full CI run on the new image, including the release workflow via a dry-run tag.
