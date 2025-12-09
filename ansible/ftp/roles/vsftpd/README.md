# This role installs and configures vsftpd (Very Secure FTP Daemon) on Ubuntu systems.

Reference Guide: https://documentation.ubuntu.com/server/how-to/networking/ftp/

Variables (defaults):
- vsftpd_listen: true
- vsftpd_listen_ipv6: false
- vsftpd_local_enable: true
- vsftpd_write_enable: true
- vsftpd_local_umask: 022
- vsftpd_chroot_local_user: true

The role provides a template for /etc/vsftpd.conf and will ensure the vsftpd service is enabled.
