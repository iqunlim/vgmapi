terraform {
  # YOU MUST RUN backend-setup IN ORDER TO UTILIZE THIS PROJECT, OTHERWISE IT WILL FAIL
  #backend "s3" {
  #  bucket         = "terraform-state-files"
  #  key            = "/vgm-project/terraform.tfstate"
  #  region         = "us-west-1"
  #  dynamodb_table = "terraform-state-locking"
  #  encrypt        = true
  #}

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

module "vgm-fastapi-module-west" {
    source = "../vgm-fastapi-module"

    # Variables are defined in variables.tf in the module and may have defaults
    domain = "carpedan.xyz"
    region = "us-west-1"
    ami = "ami-05c969369880fa2c2" # us-west-1 ubuntu 22.04 AMI
    instance_type = "t2.micro"
}