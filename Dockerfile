FROM ubuntu:22.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV TERRAFORM_VERSION=1.5.0

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    unzip \
    git \
    openssh-client \
    software-properties-common \
    python3 \
    python3-pip \
    vim \
    nano \
    && rm -rf /var/lib/apt/lists/*

# Install all Python packages from requirements.txt
COPY requirements.txt .
RUN pip3 install -r requirements.txt

# Install Ansible
RUN add-apt-repository --yes --update ppa:ansible/ansible && \
    apt-get install -y ansible

# Install Ansible Netbox collection
RUN ansible-galaxy collection install netbox.netbox

# Install Python dependencies for Ansible
RUN pip3 install pymysql requests pynetbox pytz

# Install Terraform (specific version as required)
RUN wget -O /tmp/terraform.zip https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip && \
    unzip /tmp/terraform.zip -d /usr/local/bin/ && \
    chmod +x /usr/local/bin/terraform && \
    rm /tmp/terraform.zip

# Create working directory
WORKDIR /workspace

# Create user for development
RUN useradd -m -s /bin/bash developer && \
    mkdir -p /home/developer/.ssh && \
    chown -R developer:developer /home/developer

# Switch to developer user
USER developer

# Set up SSH directory with proper permissions
RUN chmod 700 /home/developer/.ssh

# Add workspace to PATH for scripts
ENV PATH="/workspace/scripts:$PATH"

# Verify installations
RUN terraform --version && ansible --version

CMD ["/bin/bash"]
