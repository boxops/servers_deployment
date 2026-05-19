# tflint configuration
# https://github.com/terraform-linters/tflint/blob/master/docs/user-guide/config.md
#
# Install tflint:
#   curl -s https://raw.githubusercontent.com/terraform-linters/tflint/master/install_linux.sh | bash
# Install the Proxmox plugin:
#   tflint --init

config {
  # Search parent directories for .tflint.hcl — lets us run from any terraform subdir
  call_module_type = "none"
}

plugin "terraform" {
  enabled = true
  preset  = "recommended"
}

# Rules — override individual rule severity here
rule "terraform_required_version" {
  enabled = true
}

rule "terraform_required_providers" {
  enabled = true
}

rule "terraform_naming_convention" {
  enabled = false  # Proxmox resource names use hyphens by convention
}

rule "terraform_documented_variables" {
  enabled = true
}

rule "terraform_documented_outputs" {
  enabled = true
}
