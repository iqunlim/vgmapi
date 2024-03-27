terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
    region = "us-west-1"
}

# Sets up a place for tf state files to end up so that we can collaboratively use this or use it for automation setups for CD
resource "aws_s3_bucket" "terraform_state_files" {
    bucket        = "terraform-state-files"
    force_destroy =  true 
}

resource "aws_s3_bucket_service_side_encryption_configuration" "terraform_state_encryption_conf" {
    bucket        = aws_s3_bucket.terraform_state_files.bucket
    rule {
        apply_server_side_encryption {
            sse_algorithm = "AES256"
        }
    }
}

# The hash key for locking dynamodb table for remote MUST be name LockID with type S or remote backend will fail
resource "aws_dynamodb_table" "terraform_locks" {
  name         = "terraform-state-locking"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"
  attribute {
    name = "LockID"
    type = "S"
  }
}
