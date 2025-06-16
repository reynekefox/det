{ pkgs }: {
  deps = [
    pkgs.python311Full  # или ваша версия Python
    pkgs.rsync
    pkgs.openssh
  ];
}
