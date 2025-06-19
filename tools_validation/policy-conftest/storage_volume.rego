deny[msg] {
    input.kind == "PersistentVolumeClaim"
    not input.spec.storageClassName
    msg = "PersistentVolumeClaim must specify a storageClassName"
}