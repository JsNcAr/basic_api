# Releasing

How to publish a version of the API, and how to write the notes people read on
the release page. The starter itself is never released (see
[The starter and its clones](#the-starter-and-its-clones)); this page is for a
project built from it.

## How a release is put together

```text
CHANGELOG.md "Unreleased"  -->  scripts/release.py prepare  -->  commit + tag vX.Y.Z  -->  push
                                                                                           |
release page (notes, wheel, sdist)  <--  publish  <--  build  <--  lint + test  <--  verify  <-+
```

- **The notes** are the `## [Unreleased]` section of [CHANGELOG.md](../CHANGELOG.md).
  The script renames it to the version; the pipeline publishes that section as
  the release notes, word for word.
- **The script** (`scripts/release.py`) bumps the version, updates the
  changelog, commits, tags, and pushes. The version lives in one place,
  `[project] version` in `pyproject.toml`; the app reads it from the installed
  package metadata (`APP_VERSION`, shown by `GET /` and the OpenAPI document).
- **The pipeline** runs on the pushed tag, on either host:
  1. **verify**: the tag matches `pyproject.toml` and the notes exist.
  2. **lint and test**: the same jobs as a pull or merge request, PostgreSQL
     included.
  3. **build**: the wheel and the sdist (`poetry build`).
  4. **publish**: one release, created only when everything passed.

  On GitHub that is `.github/workflows/release.yml` (a GitHub release with the
  archives attached, marked pre-release when the version has a suffix). On
  GitLab it is the tag pipeline in `.gitlab-ci.yml` (a GitLab release created
  with `glab`; the archives go to the project's generic package registry and
  are linked from the release page). Both repositories can hold both files; a
  host ignores the other's.

## Choosing the version

[Semantic Versioning](https://semver.org/), applied to the HTTP contract: what
a client of this API would notice.

| Release contains | Command | Example |
|---|---|---|
| Only bug fixes, dependency updates, internal changes | `prepare patch` | 0.2.0 to 0.2.1 |
| A new route, a new optional field, a new setting | `prepare minor` | 0.2.1 to 0.3.0 |
| A changed or removed route, field, status code or error shape; a new required setting | `prepare major` (from 1.0.0); below 1.0.0, `prepare minor` with the break under **Breaking changes** | 1.2.0 to 2.0.0 |
| First stable release | `prepare 1.0.0` | 0.9.0 to 1.0.0 |

The commit type cannot tell the script that a `feat` broke a client; you choose
the part. For a test deployment ahead of a release, give an explicit
pre-release version: `prepare 1.0.0-rc.1`. It is published as a **pre-release**,
so GitHub does not show it as "Latest" (GitLab has no pre-release flag; the
suffix in the name is the signal). A later `prepare patch|minor|major` from
`1.0.0-rc.N` finishes it as `1.0.0`.

A pre-release spelled `1.0.0-rc.1` is valid PEP 440, and the installed metadata
normalises it: `GET /` reports `1.0.0rc1`. The tag and the changelog keep the
spelling you typed.

## Step by step

### 1. Write the notes

Make sure the **Unreleased** section of `CHANGELOG.md` describes everything
since the last release (see [Writing the notes](#writing-the-notes)). Each pull
request should already have added its entry, so this is a read-through. Merge
any edits to `main` like any other change.

### 2. Check `main`

```bash
git switch main
git pull
```

The script runs the full test suite before it writes anything, so the machine
you release from needs the test database (see [Setup](setup.md#testing)).

### 3. Preview

```bash
poetry run python scripts/release.py prepare minor --dry-run
```

This prints the new version, the notes exactly as they will be published, and
any local commits that would be pushed with them. It changes nothing.

### 4. Release

```bash
poetry run python scripts/release.py prepare minor
```

The script:

1. Refuses to continue if the project is the starter, you are not on `main`,
   have uncommitted changes, are behind `origin/main`, or the tag exists.
2. Runs `pytest`.
3. Writes the version into `pyproject.toml`.
4. Moves the Unreleased notes under `## [X.Y.Z] - <today>`, leaving Unreleased
   empty.
5. If `$EDITOR` (or `$VISUAL`) is set, offers to open `CHANGELOG.md` for a last
   edit.
6. Asks, then commits `chore(release): vX.Y.Z` and creates an annotated tag
   holding the notes.
7. Reinstalls the project (`poetry install --only-root`) so a running dev
   server reports the new version; the installed metadata is written at
   install time, not read from `pyproject.toml`.
8. Asks, then pushes `main` and the tag in one atomic push, which starts the
   pipeline, and prints where to watch it.

Answer **no** at the push question, or pass `--no-push`, to stop with
everything still local. Push later with the command it prints, or undo with:

```bash
git tag -d vX.Y.Z && git reset --hard HEAD~1
```

Other options: `--skip-tests` when you have just run them; `--yes` answers every
question, for scripted use; `--allow-branch` releases from another branch.

### 5. Watch the pipeline and check the release

Open the repository's **Actions** tab (GitHub) or **Build > Pipelines**
(GitLab). The release appears under **Releases** (GitHub) or **Deploy >
Releases** (GitLab) when the last job finishes. Check that the notes read
correctly, the wheel and the sdist are attached, and a deployment of the tag
answers the new version on `GET /`.

On GitLab, the first release of a project is also the first test of the job
token's rights: if `release` fails uploading the archives (a 401 or 403 from
the package registry), check that **Settings > General > Visibility > Package
registry** is on and that the job token is allowed to reach the project
(**Settings > CI/CD > Job token permissions**). Nothing was published; fix and
rerun the job.

## The starter and its clones

The starter keeps `version = "0.1.0"` and never tags: `prepare` refuses while
`pyproject.toml` has

```toml
[tool.release]
starter = true
```

A project built from the starter sets it to `false` once (it is in the
[Adapting this starter](setup.md#adapting-this-starter) list) and inherits the
script, both pipelines, the test and this page unchanged; nothing in them names
the project. The first release works from a repository with no tags: the
Unreleased section is the notes, and if it is empty the script lists every
conventional commit in the history, so write the section. Start wherever the
project is: `prepare minor` for `0.2.0`, or `prepare 1.0.0`.

The script is self-contained, so a clone can take later improvements to it with
a cherry-pick from the starter.

## Writing the notes

### Where it lives and when to write it

Everything under `## [Unreleased]` in `CHANGELOG.md` becomes the release notes.
Add entries **in the same pull request as the change**, while you still
remember why it matters, with the PR number: `(#12)`.

If Unreleased is empty at release time, the script generates the notes from the
commit subjects (see [Generated notes](#generated-notes)). That fallback is
complete but terse; prefer written notes for anything a client developer will
read.

### Structure

`###` headings, in this order, leaving out any that would be empty:

| Heading | For |
|---|---|
| `### Breaking changes` | Anything a client has to change for, plus what to do |
| `### Added` | New routes, fields, settings |
| `### Changed` | Changes to existing behaviour |
| `### Performance` | Faster or lighter, with a number when you measured one |
| `### Fixed` | Bugs fixed, described as the symptom that is gone |
| `### Removed` | Routes, fields or settings taken out |
| `### Security` | Vulnerability fixes and hardening |
| `### Dependencies` | Version moves that matter to a deployment (a new Python or PostgreSQL minimum) |
| `### Documentation` | Docs a client developer would care about |

One or two plain sentences above the first heading may summarise the release.

### Style

- **Write for the people who deploy or call the API**, not for the code: the
  route, the header, the setting, the status code.
- **One entry per change, one or two lines**, starting with the thing that
  changed. Leave the reasoning to the PR.
- **Breaking changes say what to do**: the new field name, the new minimum, the
  migration step.
- **Leave out housekeeping**: refactors with no visible effect, CI, tests,
  dependency bumps that change nothing for a deployment.

### Generated notes

With Unreleased empty, `prepare` builds the notes from the commit subjects
since the last tag, read as [Conventional Commits](https://www.conventionalcommits.org/)
(`type(scope): summary`):

| Commit type | Published under |
|---|---|
| `feat` | Added |
| `fix` | Fixed |
| `perf` | Performance |
| `refactor` | Changed |
| `security` | Security |
| `docs` | Documentation |
| `!` after the type (`feat!:`), or `BREAKING CHANGE:` in the body | Breaking changes |
| `chore`, `ci`, `test`, `build`, `style`, merge commits, other subjects | left out |

Each entry is the summary with its scope in bold and the short commit hash.

### Changing notes later

- **Before committing:** accept the script's offer to open `CHANGELOG.md`.
- **After committing, before pushing:** undo (`git tag -d vX.Y.Z && git reset
  --hard HEAD~1`), fix Unreleased, run `prepare` again.
- **After publishing:** fix the version's section in `CHANGELOG.md` through a
  normal PR, then update the release page:

  ```bash
  python scripts/release.py notes X.Y.Z > notes.md
  gh release edit vX.Y.Z --notes-file notes.md        # GitHub
  glab release create vX.Y.Z --notes-file notes.md    # GitLab: updates an existing release
  ```

  The annotated tag keeps the original text; that is expected.

## Troubleshooting

| Problem | What to do |
|---|---|
| `prepare` says this is the starter | You are in the starter, or the clone still has `starter = true`; set it to `false`. |
| `prepare` says `main` is behind `origin/main` | `git pull`, then run it again. |
| `prepare` says "nothing to release" | Unreleased is empty and no `feat`, `fix`, `perf`, `refactor`, `security` or `docs` commits exist since the last tag. Write the notes. |
| Tests fail in `prepare` | Nothing was written. Fix on `main` first. |
| The push was rejected (branch protection on `main`) | Nothing was pushed: the push is atomic. Allow the push for the release commit, or push it through a PR and push the tag after merging (`git push origin vX.Y.Z`; the tag must point at the merged commit). |
| *verify* fails | The tag was not made by the script, or `pyproject.toml` was edited by hand. Delete the tag (`git push --delete origin vX.Y.Z && git tag -d vX.Y.Z`), fix, release again. Nothing was published. |
| *lint*, *test* or *build* fails | Nothing is published. A flaky runner: rerun the failed job. Code at fault: fix on `main`, delete the tag as above, release the next patch version rather than reusing the number. |
| *publish* (GitHub) or *release* (GitLab) fails | Rerun the failed job; the archives from *build* are reused. |
| `GET /` still shows the old version on your machine | `poetry install --only-root`. |

Never re-point or reuse a tag that has a published release. Release the next
patch version instead.

## Hotfixes

Merge the fix to `main` with a `### Fixed` entry under Unreleased, then
`prepare patch`. Everything else on `main` since the last release ships with
it; release often enough that `main` is never far from releasable.
