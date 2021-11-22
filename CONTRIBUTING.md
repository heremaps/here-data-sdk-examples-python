# Contributing to HERE Data SDK Examples for Python

Thank you for taking the time to contribute.

The following is a very short set of guidelines for contributing to this package.
These are mostly guidelines, not rules. Use your best judgement and feel free to propose
changes to this document in a [pull request](https://github.com/heremaps/here-data-sdk-examples-python/pulls).

## Coding Guidelines

Given that this package consists almost of notebooks only we kindly request to adopt
[PEP8 guidelines](https://www.python.org/dev/peps/pep-0008/) as much as applicable in all
cells of any contributed notebook. More tooling to help with this will likely follow, soon.

All example notebooks are provided in [/tutorials](./tutorials).

## Signing each Commit

When you file a pull request, we ask that you sign off the
[Developer Certificate of Origin](https://developercertificate.org/) (DCO) in each commit.
Any Pull Request with commits that are not signed off will be rejected by the
[DCO check](https://probot.github.io/apps/dco/).

A DCO is a lightweight way to confirm that a contributor wrote or otherwise has the right
to submit code or documentation to a project. Simply add `Signed-off-by` as shown in the example below
to indicate that you agree with the DCO.

The git flag `-s` can be used to sign a commit:

```bash
git commit -s -m 'README.md: Fix minor spelling mistake'
```

The result is a signed commit message:

```
README.md: Fix minor spelling mistake

Signed-off-by: John Doe <john.doe@example.com>
```
