# VPC configuration
resource "aws_vpc" "fastapi-vpc" {
    cidr_block = "10.0.0.0/16"
    instance_tenancy = "default"
    

    tags = {
        Name = "fastapi-vpc"
    }
}

# Subnet needs 

resource "aws_internet_gateway" "gw" {
    vpc_id = aws_vpc.fastapi-vpc.id

    tags = {
        Name = "main"
    }

}

resource "aws_route_table" "MAIN" {
    vpc_id = aws_vpc.fastapi-vpc.id 

    route {
        cidr_block = "0.0.0.0/0"
        gateway_id = aws_internet_gateway.gw.id
    }
}

# TODO: add private Route table and associate NAT gateway for later.

# Subnets

resource "aws_subnet" "public-1" {
    vpc_id = aws_vpc.fastapi-vpc.id 
    cidr_block = "10.0.1.0/24"

    tags = {
        Name = "public-1"
        Availability = "public"
    }
}

resource "aws_subnet" "private-1" {
    vpc_id = aws_vpc.fastapi-vpc.id 
    cidr_block = "10.0.2.0/24"

    tags = {
        Name = "private-1"
        Availability = "private"
    }
}

# Associations
resource "aws_route_table_association" "public-1" {
    subnet_id = aws_subnet.public-1.id
    route_table_id = aws_route_table.MAIN.id
}

# TODO: Private-1 association

# Security Groups - Currently allows all inbound no outbound

resource "aws_security_group" "instances" {
  name = "${var.app_name}-instance-security-group"
  vpc_id = aws_vpc.fastapi-vpc.id
}

resource "aws_security_group_rule" "allow_http_inbound" {
  type = "ingress"
  security_group_id = aws_security_group.instances.id
  from_port = 8080
  to_port = 8080
  protocol = "tcp"
  cidr_blocks = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "icmp_allow_inbound" {
    security_group_id = aws_security_group.instances.id
    type = "ingress"
    from_port = -1
    to_port = -1
    protocol = "icmp"
    cidr_blocks = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "ssh_allow_inbound" {
    security_group_id = aws_security_group.instances.id
    type = "ingress"
    from_port = 22
    to_port = 22
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
}

resource "aws_security_group_rule" "allow_all_outbound" {
    security_group_id = aws_security_group.instances.id
    type = "egress"
    from_port = 0
    to_port = 65535
    protocol = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
}