terraform {
  required_providers {
    proxmox = {
      source  = "Telmate/proxmox"
      version = "3.0.2-rc03"
    }
  }
  required_version = ">= 1.0"
}

provider "proxmox" {
  pm_api_url          = var.proxmox_api_url
  pm_api_token_id     = var.proxmox_api_token_id
  pm_api_token_secret = var.proxmox_api_token_secret
  pm_tls_insecure     = var.proxmox_tls_insecure
}

# Create Example VM
resource "proxmox_vm_qemu" "example" {
  name        = "example"
  target_node = var.proxmox_node
  vmid        = 101
  onboot      = true
  
  # Clone from template
  clone = var.vm_template
  
  # Memory and CPU configuration
  memory  = 4096

  cpu {
    cores   = 2
    sockets = 1
    numa    = true
  }
  
  # Hardware configuration
  scsihw   = "virtio-scsi-pci"
  bootdisk = "scsi0"
  boot     = "c"
  qemu_os  = "other"
  
  # Disk configuration
  disks {
    scsi {
      scsi0 {
        disk {
          storage = var.proxmox_storage
          size    = "20G"
          backup  = true
          emulatessd = true
          format  = "raw"
          discard = false
          iothread = false
          readonly = false
          replicate = true
        }
      }
    }
    ide {
      ide2 {
        cloudinit {
          storage = var.proxmox_storage
        }
      }
    }
  }
  
  # Network configuration
  network {
    id      = 0
    model   = "virtio"
    bridge  = var.proxmox_bridge
    mtu     = 0
    queues  = 0
    rate    = 0
    tag     = 0
  }
  
  # Cloud-init configuration
  ciuser = "ubuntu"
  cipassword = "ubuntu"
  ipconfig0 = "ip=10.0.1.100/24,gw=10.0.1.1"
  nameserver = "1.1.1.1"
  sshkeys = <<EOF
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCw9NM2d/H4RafoHgqTS61xD7nIoNTffTaEzuUILGqgrF8nVECXh0WegpRUImkPjOMRniBWl4bdhFaoY2Tz2D5AjdKUqFkNgOuDqAvEnAB1pXMoLGt4Z4Ug428w6YnQ3qvKJDw42bcMFcEPaVoNyr+lkSQk0jRbRDueryzPPQA+1bf3QDO9/5lQxh8qWqdP5ZE/2JoeXAxYl1O+CmWHSjdPRB/oU4cx+EEWhq83nhu+UXkPJI+4xCDtILxBUyOcbDmlXka15HKIv7lW0hSKcA1L3Zv2kGeFVl2G0N3YlFRRUr6cVM/CbPP+Bv2Ns4tiP+4A+xYeXudtHf59ZG790Ygl6XTvdEqmhdedXDfuAx9IhvUl5VgA/EC3KM3NVuyktLBVtTYqW/Tl/cWks+X3csXcT6W4Aq1uLl77O3Qsok4+m1Q8MnU0HNz9G5Nyz8D1D0KWvnek5Nm9oQzjgXf+Tl4X6TluRrHT/WFZfGqYljZoS+JMML5VuXH+wJHEB9H7AJk= bal@AB-LAP-MP27ND4P
  EOF
  
  # Serial console
  serial {
    id   = 0
    type = "socket"
  }
  
  # Settings for proper VM creation
  full_clone = true
  define_connection_info = true
  
  # Tags for identification
  tags = "example,server"
}
