resource "aws_instance" "instance_1" {
  ami             = var.ami
  instance_type   = var.instance_type
  subnet_id = aws_subnet.public-1.id
  security_groups = [aws_security_group.instances.id]
  associate_public_ip_address = true
  user_data       = <<-EOF
              #!/bin/bash
              echo "Hello, World 1" > index.html
              python3 -m http.server 8080 &
              EOF
}