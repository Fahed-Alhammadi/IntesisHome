# Security Policy

## Supported Versions

Only the latest release of the IntesisHome integration receives security fixes. Please update to the newest version (via HACS or the [releases page](https://github.com/Fahed-Alhammadi/IntesisHome/releases)) before reporting an issue.

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues, discussions, or pull requests.**

Report them privately through GitHub's private vulnerability reporting:

1. Go to the [Security tab](https://github.com/Fahed-Alhammadi/IntesisHome/security) of this repository.
2. Click **Report a vulnerability**.
3. Fill in the advisory form.

Please include as much of the following as you can:

- A description of the vulnerability and its impact
- The integration version, Home Assistant version and cloud service (IntesisHome, airconwithme or anywAiR)
- Steps to reproduce, or a proof of concept
- Any relevant logs, **with usernames, passwords, tokens, device IDs and IP addresses removed**

### What to expect

- **Acknowledgement** within 7 days of your report.
- **Assessment** and a decision on whether the issue is accepted within 14 days.
- **Fix and disclosure**: accepted issues are fixed in a new release as soon as practical. A GitHub Security Advisory is published once a fix is available, and you will be credited unless you prefer to stay anonymous.

This is a community project maintained in spare time, so timelines are best effort.

## Scope

**In scope**: code in this repository (`custom_components/intesishome/`), for example:

- Credentials or session tokens leaked to logs, diagnostics, entity attributes or the UI
- Unsafe handling of data received from the cloud service
- Flaws in the config or reauthentication flow

**Out of scope** (please report these to the right party instead):

- Vulnerabilities in [`pyintesishome`](https://github.com/jnimmo/pyIntesisHome): report them to that project.
- Vulnerabilities in the IntesisHome, airconwithme or anywAiR cloud services, apps or hardware: report them to the vendor.
- Vulnerabilities in [Home Assistant](https://www.home-assistant.io/security/) itself.
- Issues that require an attacker to already have administrator access to your Home Assistant instance.

## Keeping Your Setup Secure

- Your cloud username and password are stored in Home Assistant's config entry storage. Protect your Home Assistant instance and its backups accordingly.
- Use a unique password for your IntesisHome / airconwithme / anywAiR account.
- Before sharing debug logs publicly, remove credentials, tokens, device IDs and IP addresses.
