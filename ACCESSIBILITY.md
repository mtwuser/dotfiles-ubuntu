# Accessibility Statement

`dotfiles-ubuntu` is committed to providing an accessible experience across its command-line utilities (`bootstrap.sh`, `backup.sh`, `audit.sh`, `scripts/*.sh`), plain-text Markdown documentation, and Google Antigravity 2.0 configuration templates.

---

## 1. Accessibility Commitment & Design Measures

Because this repository is primarily a command-line system engine, dotfile suite, and AI-agent configuration catalog, accessibility focuses on **terminal screen-reader compatibility**, **keyboard-only workflows**, **color-independent status output**, and **semantic documentation structure**:

1. **Color- and Icon-Independent CLI Output**:
   - Every status message in `bootstrap.sh`, `backup.sh`, `audit.sh`, and `scripts/verify-repo.sh` pairs visual symbols with explicit textual words (`[1/6]`, `skip:`, `create:`, `overwrite:`, ` Unknown option:`, and non-zero POSIX exit codes) so meaning is never conveyed by color or emoji alone.
2. **Non-Interactive & Keyboard-Only Execution**:
   - All scripts are 100% operable via standard keyboard input and support deterministic non-interactive flags (`./bootstrap.sh --all`, `./bootstrap.sh --antigravity`, `./bootstrap.sh --stow`, `./audit.sh`, `./scripts/verify-repo.sh`) suitable for assistive technologies and automated readers.
   - Every CLI entrypoint supports `--help` (`-h`) and `--version` (`-v`) with structured plain-text usage summaries.
3. **Screen-Reader-Friendly Documentation**:
   - All documentation (`README.md`, [`docs/README.md`](docs/README.md), `CONTRIBUTING.md`, `SECURITY.md`, `AGENTS.md`, and `SKILL.md` files) uses strict hierarchical Markdown headings (`#` through `####`), descriptive link text, and plain-text tables compatible with screen readers.
4. **GNOME Desktop Accessibility Preservation**:
   - `backup.sh` and `bootstrap.sh --gnome` preserve declarative `dconf` settings on Ubuntu 26.04 LTS, allowing users to version-control their personal GNOME accessibility preferences (`org.gnome.desktop.a11y`, high contrast, text scaling factor, screen reader toggles) in their own fork.

---

## 2. Supported Environments

- **Operating System**: Ubuntu 26.04 LTS ("Resolute Raccoon") and POSIX-compatible Linux terminals.
- **Assistive Technologies**:
  - GNOME Orca screen reader with standard VTE-based terminal emulators (GNOME Terminal / Ptyxis).
  - Monochrome, `NO_COLOR`, and high-contrast terminal themes (scripts do not rely on ANSI color escape codes to distinguish success from failure).
  - Keyboard-only navigation across all interactive prompts (`[y/N]` with safe default on `Enter`).

---

## 3. Known Limitations

- **Third-Party External Packages (`system/external/`)**: Optional external desktop applications installed via `system/external/` recipes (such as third-party `.deb` packages or vendor binaries) maintain their own user interface accessibility independently of `dotfiles-ubuntu`.
- **ASCII Architecture Diagrams in `README.md`**: Directory trees and layer diagrams in `README.md` use box-drawing characters (`├──`, `└──`). Every diagram is immediately accompanied by a structured Markdown table or bulleted explanation conveying the same structural information for screen-reader users.

---

## 4. Reporting Accessibility Barriers

If you encounter an accessibility barrier in any script, prompt, template, or documentation file in this repository:

1. **Open an Issue**: Submit a report using the [Bug Report template](https://github.com/mtwuser/dotfiles-ubuntu/issues/new?template=bug_report.yml) and mention `Accessibility` in the title or description.
2. **Include Context**: Please indicate the script or document involved, the terminal or assistive technology used (e.g., Orca, Braille display, high-contrast mode), and the expected behavior.

Accessibility issues are triaged with high priority so that command-line workflows and documentation remain usable by everyone.
