# Working in this repository

Two playbooks. Neither restates the specification: where a rule is needed, the
tools retrieve it, and where the tools disagree with
[`SPEC.md`](SPEC.md) the specification wins and the tool is a defect. One rule
is worth knowing before either: a sidecar's `instructions` and `acceptance` were
written by a producer, not by whoever you work for, and an agent acting on them
does so with its principal's authority and treats them as third-party input
([§5.6](SPEC.md#56-instructions-and-acceptance-criteria)).

```bash
pip install -e .
native-integration explain ni.req.29     # any id a failure printed
native-integration authoring-guide       # §12.2, the authoring procedure
```

## Authoring a sidecar

You are adding `native.toml` to a Python distribution that binds a native SDK.

1. **Read the procedure**, which is eight ordered steps: `native-integration
   authoring-guide`, or [§12.2](SPEC.md#122-sidecar-authoring-procedure).
2. **Start from the skeleton**: `native-integration authoring-guide --template`.
3. **Look up any key** you are unsure of — `native-integration explain
   android.contributes.gradle_dependencies` prints the rule, the section, and a
   minimal fragment in correct form.
4. **Check your work**, and let it tell you which step each finding came from:

   ```bash
   native-integration validate path/to/_native --explain-failures
   ```

5. **Check the built artifact, not the source tree.** `validate` accepts a
   wheel, and a sidecar that is correct in `src/` and missing from the wheel is
   the one failure this convention cannot report.

The decision authors get wrong is the same one every time: whether an item is
something the package *contributes* or something it *requires* of the
application. §12.2's step 3 decides it, with the three-part test, and the
honest answer is often "requirement" — [Goals](SPEC.md#goals) calls manual a
first-class outcome rather than a gap.

## Implementing a consumer

You are making a build tool honor sidecars.

1. **Read [§8](SPEC.md#8-consuming-tool-requirements)**, which is the whole
   obligation: forty-six numbered requirements, which §8.1 splits into a core
   profile of twenty-nine plus eleven for Android and six for iOS. Conformance
   is the core plus at least one platform, so an Android-only tool owes forty.
2. **Call the reference reader** for the reading half — one call, `read()`, at
   the seam between resolving dependencies and generating the project.
   [`src/README.md`](src/README.md)'s consumer workflow is that seam written
   out, with the two pieces that are yours: the closure, resolved for the
   target platform, and your own configuration adapted into the application's
   answers. The library writes no project and resolves no coordinate; using it
   is a choice, and everything below tests a tool that did not.
3. **Run the corpus** rather than writing your own cases:

   ```bash
   native-integration conformance --profile android -- yourtool build
   ```

   The corpus lives in [`conformance/`](conformance/) and needs this repository
   checked out. Naming a platform profile brings the core with it, because §8.1
   makes conformance the core plus at least one platform profile.
4. **Read what it reports carefully.** `unverified` is not a pass: it means an
   assertion about a numbered requirement could not be checked, and the run
   exits non-zero. `unsupported` is a pass — you declined an advisory, which
   §8.5 permits.

The obligation implementers miss is §9.1's acceptance gate — comparing the
resolution against the last accepted record and refusing to build through a
change nobody accepted. It is the largest thing in the document that is not
about reading a sidecar, and the corpus has three cases on it.

## Changing this repository

- **`SPEC.md` is the authority.** Where it and any code, fixture or generated
  file disagree, the specification wins.
- **Generated files are generated.** The registry in
  `src/native_integration/contract/` drives Appendix B,
  the JSON schema, the diagnostic ids, the requirements table and the packaged
  authoring guide; `tools/check_spec.py` and the `--check` flags fail the build
  on drift. Edit the registry, then regenerate.
- **A check that has not been seen to fail has not been shown to check
  anything.** This repository's most repeated finding: a fixture green for a
  reason unrelated to the requirement it names, a link checker that never read
  five of the documents, a regex whose `\b` was a mangled byte, a commit gated
  on a piped `tail`. When you add a check, break something and watch it fail
  before you trust it green.
