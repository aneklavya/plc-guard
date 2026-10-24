# 6. Web UI and deployment

## The Streamlit app (`app.py`)

**Streamlit** turns a Python script into a web app: the script re-runs top to
bottom on every click, and `st.*` calls draw widgets. Good for research demos
because there is no separate front-end code.

Run it: `pip install -r requirements-app.txt && streamlit run app.py`, then
open <http://localhost:8501>.

### What a visitor sees

- **Sidebar:** choose Rules, LLM (Nemotron) or Both; optional field for the
  visitor's own NVIDIA key; a counter of live scans left.
- **Scan tab:** pick one of the 20 example programs (default: the conveyor
  with the logic bomb) or paste code; tick "Rename all variables" to run the
  robustness test live; press Scan. Results are a table (line, type, CWE, which
  detector, the code line, explanation). For examples, an expander shows the
  ground-truth label.
- **Evaluation results tab:** the summary table from `results/runs.jsonl` and
  a precision / recall / F1 bar chart.
- **About tab:** what the project is and the 8 classes.

Best demo: the conveyor example with "Rename all variables" ticked. The rules
lose the MISSING_INTERLOCK finding and the LLM keeps it, which is the main
result of Stage 2 shown live.

### Protecting the API key and quota

| Situation | Behaviour |
|---|---|
| Scanning an example program (original or renamed) | Answer comes from the committed cache. No API call, no quota used. Recognised by comparing the code's lines with the dataset. |
| Pasting new code, visitor gave their own key | Their key is used, no limit, nothing stored. |
| Pasting new code, no key | Server key (`NVIDIA_API_KEY`) is used, max `PLCGUARD_SESSION_LIMIT` (5) per browser session and `PLCGUARD_DAILY_LIMIT` (200) per day for everyone. |
| Pasted code | Limited to 20,000 characters. Only analysed, never executed, and live replies are not written to the cache. |

The daily counter lives in memory (`st.cache_resource` with a lock), so it
resets if the app restarts. Good enough for a demo, not for production.

## Docker

The `Dockerfile` builds a small image: `python:3.13-slim`, install Streamlit,
copy `plcguard/`, `dataset/`, `results/` and `app.py`, run as a non-root user,
expose port 8501. `.dockerignore` keeps `.env`, `.git`, tests and infra out of
the image, so the key is never baked in; it is passed at run time:

```bash
docker build -t plcguard .
docker run -p 8501:8501 --env-file .env plcguard
```

(Not yet tested on this laptop because Docker Desktop was not running.)

## AWS with Terraform (`infra/terraform/`, written, not applied)

**Terraform** describes infrastructure as code: you write what should exist,
`terraform plan` shows the changes, `terraform apply` makes them, `terraform
destroy` removes everything. The state of what exists is kept in a
`terraform.tfstate` file (gitignored here).

What it creates:

| Resource | Purpose |
|---|---|
| `aws_instance` (t3.micro, Amazon Linux 2023) | The server. Free-tier eligible. 20 GB encrypted gp3 disk. IMDSv2 required. |
| `aws_security_group` | Opens only port 8501 (to `allowed_cidrs`, default everyone). **No SSH port.** |
| `aws_iam_role` + instance profile | Lets the server use SSM Session Manager (shell access without SSH) and read one parameter. |
| `aws_iam_role_policy` | Allows `ssm:GetParameter` on `/plcguard/nvidia_api_key` only (least privilege). |

At boot, `user_data.sh.tftpl` installs Docker and git, adds 2 GB of swap (a
1 GB machine needs it to build the image), clones the GitHub repo, builds the
image, reads the key from SSM Parameter Store, and starts the container with
`--restart unless-stopped`.

**Why the key goes through SSM and not Terraform:** anything passed as a
Terraform variable ends up in plain text in the state file. Creating the
parameter yourself keeps the key out of Terraform completely:

```bash
aws ssm put-parameter --name /plcguard/nvidia_api_key --type SecureString --value nvapi-...
cd infra/terraform
terraform init
terraform plan      # read it before applying
terraform apply     # prints the URL; wait a few minutes for the Docker build
terraform destroy   # when finished, to stop any charges
```

**AWS free tier note:** accounts created after 15 July 2025 get credits (up
to about $200, valid 6 months) instead of the old 12-month free tier. Set a
billing alarm either way.

Next: [Decision log](07-decision-log.md)
