# Security Policy

## Supported Versions

| Version | Supported |
| :--- | :--- |
| 1.0.x | ✅ |
| < 1.0 | ❌ |

Only the latest stable release receives security updates. Pre-release and beta versions are unsupported.

---

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Report privately by emailing: **rahul@iiitm.ac.in**  
Include `[VidChain Security]` in the subject line.

### What to include

- A clear description of the vulnerability and its potential impact
- Steps to reproduce or a proof-of-concept
- Affected version(s)
- Any suggested fix, if you have one

### What to expect

- **Acknowledgement** within 48 hours
- **Status update** within 7 days — whether the report is accepted, needs more info, or is out of scope
- **Patch timeline** communicated once the issue is confirmed
- Credit in the release notes if you'd like to be acknowledged

Reports that are accepted will be addressed in a patch release as soon as possible. Reports that are declined will receive a clear explanation.

---

## Scope

VidChain runs entirely on local hardware. There is no cloud backend, no telemetry, and no data transmission. Security concerns most relevant to this project include:

- Malicious or crafted video/audio files triggering unsafe behavior during ingestion
- Path traversal or unsafe file handling in the CLI or API layer
- Dependency vulnerabilities in the Python or Node.js packages
- Unauthorized access to the local FastAPI server when exposed on a network

Out of scope: vulnerabilities in upstream models (Ollama, Whisper, YOLO, etc.) — please report those to their respective maintainers.

---

**Author:** Rahul Sharma — IIIT Manipur  
**License:** MIT
