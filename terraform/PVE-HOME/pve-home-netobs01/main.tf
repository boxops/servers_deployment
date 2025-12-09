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

# Create NetBox VM
resource "proxmox_vm_qemu" "pve-home-netobs01" {
  name        = "pve-home-netobs01"
  target_node = var.proxmox_node
  vmid        = 104
  onboot      = true
  
  # Clone from template
  clone = var.vm_template
  
  # Memory and CPU configuration
  # 16 GB
  memory  = 16384
  
  cpu {
    cores   = 4
    sockets = 4
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
          size    = "100G"
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
  ipconfig0 = "ip=10.0.1.102/24,gw=10.0.1.1"
  nameserver = "1.1.1.1"
  
  # Serial console
  serial {
    id   = 0
    type = "socket"
  }
  
  # Settings for proper VM creation
  full_clone = true
  define_connection_info = true
  
  # Tags for identification
  tags = "netobs"
}
