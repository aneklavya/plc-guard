variable "region" {
  type    = string
  default = "us-east-1"
}

variable "instance_type" {
  description = "Free-tier eligible: t3.micro (or t2.micro in older regions)."
  type        = string
  default     = "t3.micro"
}

variable "allowed_cidrs" {
  description = "Who can open the app. Use [\"<your-ip>/32\"] while testing."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "repo_url" {
  type    = string
  default = "https://github.com/aneklavya/plc-guard.git"
}

variable "key_parameter" {
  description = "SSM SecureString holding the NVIDIA API key (created outside Terraform)."
  type        = string
  default     = "/plcguard/nvidia_api_key"
}

variable "session_limit" {
  description = "Live LLM scans per visitor session using the server key."
  type        = number
  default     = 5
}

variable "daily_limit" {
  description = "Live LLM scans per day across all visitors using the server key."
  type        = number
  default     = 200
}
