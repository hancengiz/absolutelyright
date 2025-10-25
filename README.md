# absolutelyright

A scientifically rigorous tracking system for how often Claude Code validates my life choices.

This code powers the [https://cc.cengizhan.com/](https://cc.cengizhan.com/) website.

**Originally forked from** [yoavf/absolutelyright](https://github.com/yoavf/absolutelyright) which powers [absolutelyright.lol](https://absolutelyright.lol/)

---

<img width="1100" height="1200" alt="screenshot-rocks" src="https://github.com/user-attachments/assets/5464b87b-edb6-460c-b625-d06c33684d9a" />


## What this repo contains

- **Frontend** → minimal HTML + JS, with charts drawn using [roughViz](https://www.jwilber.me/roughviz/)
- **Backend** → Rust server (Axum + SQLite), serves the frontend and provides a tiny API
- **Scripts** → Python scripts to collect and upload counts from Claude Code sessions

**Currently tracking:**
- Times Claude Code said I'm "absolutely right"
- Times Claude Code said I'm just "right" (meh)

---

## Collecting your own data and running locally

- Check out the [scripts/README.md](./scripts/README.md) for info on how to collect your own Claude Code "you are absolutely right" counts.
- To run the server locally:

```bash
cargo run
# visit http://localhost:3003
```