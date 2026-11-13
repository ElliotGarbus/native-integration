<!-- GENERATED from SPEC.md §12.2 by tools/gen_authoring_guide.py. -->
<!-- Do not edit: the specification is the original and this is a copy. -->

### 12.2 Sidecar authoring procedure

**Non-normative, and it introduces nothing.** Every decision below is made
somewhere else in this document, and each step says where. What is added is the
*order*: the guidance above is complete and is scattered across five sections,
so an author meets it as a set of principles rather than as a sequence, and the
one place they most often guess — whether an item is a contribution or a
requirement — is decided by a test stated under [Goals](#goals) and applied in
[§2.1](#21-design-principles).

Work one item at a time. An item is a single thing the vendor's integration
documentation asks for: one dependency, one permission, one key, one console
setting.

**1. Inventory.** List every item the vendor's native integration
documentation requires, for each platform separately. These are "the things an
application author would otherwise transcribe out of a README"
([Goals](#goals)), and the list is the input to every step that follows. Do not
classify while inventorying; a half-classified list hides the items that fit no
category, and those are the interesting ones.

**2. Classify into the three categories.**
[§2.1](#21-design-principles) fixes them and what each one means:

| The item is | Category |
| --- | --- |
| An exclusive namespace the package needs to hold across the whole closure | `owns` |
| Material the package supplies and a consumer can stage on its behalf | `contributes` |
| Anything else — a condition the application or its build must satisfy | `requires` |

§2.1's own examples settle most of the list: "A Java namespace is owned. An SDK
floor, a value the application supplies, and an action it performs are
required… Source files, dependency coordinates, permissions and manifest
components are contributed."

**3. Test every candidate contribution before accepting it.** A declaration is
automated when all three hold ([Goals](#goals)):

1. the producer knows exactly what is required;
2. the consumer can do it deterministically;
3. little or no application-specific policy is involved.

[§2.1](#21-design-principles) makes this the decision between the last two
categories: "material that passes all three is a contribution, and material
that fails any of them is a requirement." A failure on any one of the three is a
failure. Run the test honestly ([§12](#12-guidance-for-package-authors)) —
it is your own work that a passing answer saves, and every application's that a
wrong one costs.

**4. For a requirement, choose the shape.** [§5](#5-requirements-on-the-application)
gives three, and the boundary between the last two is "what the consumer can
place deterministically":

| The requirement is | Shape |
| --- | --- |
| A minimum the application's build configuration must meet | Floor ([§5.1](#51-build-floors)) |
| A string the application has, whose destination the consumer knows | Value ([§5.2](#52-values)) |
| An outcome the application must achieve that the consumer cannot produce | Action ([§5.3](#53-actions)) |

Classify by what the requirement *is*, not by which shape is easier to satisfy
([§5](#5-requirements-on-the-application)). A notification icon is a drawable
someone must draw: there is no string to write, so it is an action however
convenient a value would be.

**5. Where no declaration represents the item, it is an action.** This document
does not "model every platform construct Apple and Google ship"
([Non-goals](#non-goals)), so an item with no matching declaration is expected
rather than a gap. State it as an action
([§2.1](#21-design-principles): "state it as an action rather than forcing it
into a shape the consumer cannot honor"). Do not reach for a declaration that
almost fits: "a partial automation that looks complete is worse than a clear
task", and where the artifact is the application's, a producer "states a
requirement and stops".

**6. Decide whether the requirement is unconditional.** Declare only what every
application that imports the package needs
([§12](#12-guidance-for-package-authors)). For the rest, the shape of your
package decides the mechanism:

| Your package | Mechanism |
| --- | --- |
| A facade with a packaging seam — independent features behind one dispatcher | Ship the conditional surface as separate distributions, selected by extras ([§12](#12-guidance-for-package-authors)) |
| A 1:1 binding of a platform framework, with no seam to split along | Declare the unconditional needs normally and mark the rest `conditional = true`, with the triggering condition in `reason` ([§12.1](#121-framework-bindings-where-this-guidance-does-not-apply)) |

There is no conditional *contribution*: the dependency graph is the
conditionality mechanism, and only a requirement carries the flag
([§12](#12-guidance-for-package-authors)). And `conditional` is not a way to
avoid stating an unconditional requirement
([§12.1](#121-framework-bindings-where-this-guidance-does-not-apply)) — doing
that converts a build failure that names the problem into a line in a report.

**7. Check each declaration against the reference.**
[Appendix B](#appendix-b-declaration-reference) is the complete key list, and
[§4.4](#44-unknown-declarations-fail-closed) makes a consumer fail closed on
anything it does not recognize — so a misspelling is a build failure for every
application that installs the package, not a warning. A generated JSON Schema
covers what a schema can cover: presence, types, closed vocabularies, and array
shapes.

**8. Build the distribution and confirm what shipped.** The sidecar and its
resources are only useful if they are in the artifact:

- `native.toml` is named exactly that, sits in the directory the entry-point
  value identifies, and ships as ordinary package data
  ([§4.1](#41-location-and-name));
- one sidecar covers every platform the distribution supports
  ([§4.2](#42-one-file-for-all-platforms));
- every resource a declaration references ships too, since a consumer that
  cannot read one fails naming your distribution
  ([§3.2](#32-resolution), [§4.1](#41-location-and-name));
- the distribution registers exactly one entry point in the group
  ([§3.4](#34-one-entry-per-distribution)).

Building the wheel and reading its contents is the check. A sidecar that is
correct in the source tree and absent from the artifact is the one failure this
convention cannot report, because there is nothing to report on.

> **Note: an editable install is not readable this way.**
> [§3.2](#32-resolution) reaches a sidecar through
> `Distribution.locate_file()` or `Distribution.files`, and a
> [PEP 660](https://peps.python.org/pep-0660/) editable install answers neither:
> its `files` lists a `.pth`, a finder module and the `dist-info`, and no
> sidecar at all. The real location is inside the finder, which the import
> system reads and [§3.2](#32-resolution) does not — *"nothing is imported,
> ever"*, because a distribution targeting Android or iOS may not be importable
> on the build host at all. A consumer therefore reports such a distribution as
> unreadable, which is [§3.2](#32-resolution) working rather than failing. Two
> ways round it while authoring: reinstall before each check, or point a
> validator at the sidecar directory, which reads the file directly and needs no
> install.

> **Note: a hashed input and a version-control checkout.**
> [§9.3](#93-hashed-inputs) hashes the sidecar's bytes, and the integration
> record carries the digest. A version-control system that rewrites line endings
> on checkout — Git's `core.autocrlf`, on by default on Windows — hands a fresh
> clone a `native.toml` whose digest is not the one the record was written
> against, and the next build reports a [§9.1](#91-the-lifecycle) delta for a
> change nobody made. The report is accurate and its cause is not visible in it,
> since what it names is an input digest. Pinning the line endings of the
> sidecar, of everything it references, and of the record is a property of the
> repository holding them rather than of anything this document can check.

> **Note:** The procedure stops where the specification does. It cannot tell you
> whether a vendor's SDK needs a permission — that is the vendor's
> documentation's job — and it does not decide the contribution-versus-action
> boundary for you, because the three-part test does. What it removes is the
> guessing about *which question to ask next*, which is where an author who has
> read §2, §5 and §12 separately still ends up inventing a shape.
