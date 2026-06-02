provider "aws" {
  region = var.aws_region
}

resource "aws_ecs_cluster" "main" {
  name = "repo-intelligence"
}

resource "aws_ecs_task_definition" "query" {
  family                   = "query-service"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([
    {
      name  = "query"
      image = "${aws_ecr_repository.repo.repository_url}:query-latest"
      portMappings = [
        {
          containerPort = 8080
          protocol      = "tcp"
        }
      ]
      environment = [
        { name = "DATABASE_URL", value = "postgresql+asyncpg://${aws_db_instance.main.username}:${aws_db_instance.main.password}@${aws_db_instance.main.endpoint}/repo_intelligence" }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.main.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "query"
        }
      }
    }
  ])
}

resource "aws_ecr_repository" "repo" {
  name                 = "repo-intelligence"
  image_tag_mutability = "MUTABLE"
}

resource "aws_db_instance" "main" {
  identifier        = "repo-intel-db"
  engine            = "postgres"
  engine_version    = "15.4"
  instance_class    = "db.t3.micro"
  allocated_storage = 20
  db_name           = "repo_intelligence"
  username          = "repo"
  password          = random_password.db_password.result
  skip_final_snapshot = true
}

resource "random_password" "db_password" {
  length  = 16
  special = false
}

resource "aws_s3_bucket" "storage" {
  bucket = "repo-intelligence-data-${random_id.bucket_suffix.hex}"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "aws_cloudwatch_log_group" "main" {
  name              = "/ecs/repo-intelligence"
  retention_in_days = 7
}

resource "aws_iam_role" "ecs_execution" {
  name = "repo-intel-ecs-execution"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}

variable "aws_region" {
  default = "us-east-1"
}
