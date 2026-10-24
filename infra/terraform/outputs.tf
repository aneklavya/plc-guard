output "url" {
  description = "Open this a few minutes after apply (the Docker build runs at boot)."
  value       = "http://${aws_instance.app.public_dns}:8501"
}

output "instance_id" {
  description = "Shell access: aws ssm start-session --target <id>"
  value       = aws_instance.app.id
}
