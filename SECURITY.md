# Security Policy

## Supported versions

BlackBox is in active early development. Security fixes are applied to the
`main` branch.

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Instead, report
privately via GitHub's [Security Advisories](https://github.com/Sushanth968/blackbox/security/advisories/new),
or by contacting a maintainer directly.

When reporting, please include:

- a description of the issue and its potential impact,
- steps to reproduce (a minimal evidence file or request, if applicable), and
- any suggested remediation.

We aim to acknowledge reports within a few days and will coordinate a fix and a
disclosure timeline with you.

## Scope

BlackBox ingests **untrusted evidence files** (logs, exports, archives). We are
especially interested in reports of:

- parser crashes or denial-of-service from malformed/oversized input,
- path traversal or unsafe file handling during evidence upload,
- leakage of content that the redaction layer is expected to hide, or
- integrity gaps in the evidence hashing / provenance chain.
