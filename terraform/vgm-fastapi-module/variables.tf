# Global
variable "region" {
    description = "Region to deploy this module to"
    type = string 
}

variable "app_name" { 
    description = "Name your app! Important for various resource names for clarity"
    type = string
    default = "MyAPP"
}

# EC2 
variable "ami" { 
    description = "The AMI to use for this "
    type = string
}

variable "instance_type" { 
    description = "EC2 instance type (defaults to t2.micro)"
    type = string
    default = "t2.micro"
}

# Route 53
variable "create_dns" {
    description = "Create Route53 zone, defaults to false"
    type = bool
    default = false
}

variable "domain" {
    description = "Domain name for setup with route53"
    type = string
}

# VPC
variable "vpc_name" {
    description = "Name of created VPC with the module"
    type = string
    default = "FastAPI-VPC"
}