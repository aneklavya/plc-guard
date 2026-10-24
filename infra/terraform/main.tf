# One free-tier EC2 instance running the PLCGuard Streamlit app in Docker.
#
# The NVIDIA key never passes through Terraform (so it is not in the state
# file). Store it once in SSM Parameter Store; the instance reads it at boot:
#   aws ssm put-parameter --name /plcguard/nvidia_api_key --type SecureString --value nvapi-...
# Without the parameter the app still runs (rules + cached example scans).

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = "plcguard" }
  }
}

data "aws_ssm_parameter" "al2023_ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

data "aws_vpc" "default" {
  default = true
}

data "aws_caller_identity" "current" {}

resource "aws_security_group" "app" {
  name        = "plcguard-app"
  description = "PLCGuard Streamlit UI"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Streamlit"
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = var.allowed_cidrs
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# No SSH: shell access goes through SSM Session Manager.
resource "aws_iam_role" "app" {
  name = "plcguard-app"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_core" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "read_key" {
  name = "read-nvidia-key"
  role = aws_iam_role.app.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "ssm:GetParameter"
      Resource = "arn:aws:ssm:${var.region}:${data.aws_caller_identity.current.account_id}:parameter${var.key_parameter}"
    }]
  })
}

resource "aws_iam_instance_profile" "app" {
  name = "plcguard-app"
  role = aws_iam_role.app.name
}

resource "aws_instance" "app" {
  ami                    = data.aws_ssm_parameter.al2023_ami.value
  instance_type          = var.instance_type
  iam_instance_profile   = aws_iam_instance_profile.app.name
  vpc_security_group_ids = [aws_security_group.app.id]
  user_data = templatefile("${path.module}/user_data.sh.tftpl", {
    region        = var.region
    repo_url      = var.repo_url
    key_parameter = var.key_parameter
    session_limit = var.session_limit
    daily_limit   = var.daily_limit
  })
  user_data_replace_on_change = true

  metadata_options {
    http_tokens = "required" # IMDSv2 only
  }

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
    encrypted   = true
  }

  tags = { Name = "plcguard-app" }
}
